"""
cvm_downloader.py
-----------------
Baixa dados financeiros da CVM (Comissão de Valores Mobiliários)
via portal de dados abertos: https://dados.cvm.gov.br/

Documentos suportados:
  - DFP (Demonstração Financeira Padronizada — anual)
  - ITR (Informações Trimestrais)

A CVM disponibiliza os dados como arquivos ZIP contendo CSVs separados
por tipo de demonstração e consolidação.

Uso:
    from ingestion.cvm_downloader import CVMDownloader

    dl = CVMDownloader(output_dir="data/raw/cvm")
    dl.download_dfp(year=2023)
    dl.download_itr(year=2023, quarter=4)
    files = dl.get_local_files("DFP", 2023)
"""

from __future__ import annotations

import io
import logging
import time
import zipfile
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

BASE_URL = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC"

# Tipos de demonstração disponíveis dentro do ZIP (consolidado e controladora)
DFP_DATASETS = {
    "DRE_con":   "dfp_cia_aberta_DRE_con_{year}.csv",      # DRE consolidada
    "DRE_ind":   "dfp_cia_aberta_DRE_ind_{year}.csv",      # DRE controladora
    "BPA_con":   "dfp_cia_aberta_BPA_con_{year}.csv",      # Ativo consolidado
    "BPA_ind":   "dfp_cia_aberta_BPA_ind_{year}.csv",
    "BPP_con":   "dfp_cia_aberta_BPP_con_{year}.csv",      # Passivo consolidado
    "BPP_ind":   "dfp_cia_aberta_BPP_ind_{year}.csv",
    "DFC_MI_con":"dfp_cia_aberta_DFC_MI_con_{year}.csv",   # DFC método indireto
    "DFC_MI_ind":"dfp_cia_aberta_DFC_MI_ind_{year}.csv",
    "DFC_MD_con":"dfp_cia_aberta_DFC_MD_con_{year}.csv",   # DFC método direto
    "DVA_con":   "dfp_cia_aberta_DVA_con_{year}.csv",      # DVA
}

ITR_DATASETS = {
    "DRE_con":   "itr_cia_aberta_DRE_con_{year}.csv",
    "DRE_ind":   "itr_cia_aberta_DRE_ind_{year}.csv",
    "BPA_con":   "itr_cia_aberta_BPA_con_{year}.csv",
    "BPA_ind":   "itr_cia_aberta_BPA_ind_{year}.csv",
    "BPP_con":   "itr_cia_aberta_BPP_con_{year}.csv",
    "BPP_ind":   "itr_cia_aberta_BPP_ind_{year}.csv",
    "DFC_MI_con":"itr_cia_aberta_DFC_MI_con_{year}.csv",
    "DFC_MI_ind":"itr_cia_aberta_DFC_MI_ind_{year}.csv",
}

RATE_LIMIT_SECONDS = 1.5  # Respeito ao servidor CVM


# ---------------------------------------------------------------------------
# Downloader
# ---------------------------------------------------------------------------

class CVMDownloader:
    """
    Baixa e extrai arquivos de dados abertos da CVM.

    Args:
        output_dir: Diretório base onde os arquivos serão salvos.
                    Estrutura criada: output_dir/DFP/YYYY/ ou output_dir/ITR/YYYY/
        timeout: Timeout HTTP em segundos.
    """

    def __init__(self, output_dir: str | Path = "data/raw/cvm", timeout: int = 60):
        self.output_dir = Path(output_dir)
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "FinancialIntelligencePlatform/1.0 (educational; dados.cvm.gov.br)"
        })

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def download_dfp(self, year: int) -> list[Path]:
        """
        Baixa e extrai todos os CSVs de DFP para o ano especificado.

        Returns:
            Lista de arquivos CSV extraídos.
        """
        url = f"{BASE_URL}/DFP/DADOS/dfp_cia_aberta_{year}.zip"
        dest_dir = self.output_dir / "DFP" / str(year)
        return self._download_and_extract(url, dest_dir, label=f"DFP {year}")

    def download_itr(self, year: int) -> list[Path]:
        """
        Baixa e extrai todos os CSVs de ITR para o ano especificado.
        Contém todos os trimestres do ano.

        Returns:
            Lista de arquivos CSV extraídos.
        """
        url = f"{BASE_URL}/ITR/DADOS/itr_cia_aberta_{year}.zip"
        dest_dir = self.output_dir / "ITR" / str(year)
        return self._download_and_extract(url, dest_dir, label=f"ITR {year}")

    def download_range(
        self,
        doc_type: str,
        start_year: int,
        end_year: int,
    ) -> dict[int, list[Path]]:
        """
        Baixa múltiplos anos de uma vez.

        Args:
            doc_type: "DFP" ou "ITR"
            start_year: Ano inicial (inclusive)
            end_year: Ano final (inclusive)

        Returns:
            Dicionário {ano: [arquivos]}
        """
        assert doc_type in ("DFP", "ITR"), f"doc_type deve ser DFP ou ITR, recebido: {doc_type}"
        results = {}
        for year in range(start_year, end_year + 1):
            try:
                if doc_type == "DFP":
                    files = self.download_dfp(year)
                else:
                    files = self.download_itr(year)
                results[year] = files
                time.sleep(RATE_LIMIT_SECONDS)
            except Exception as e:
                logger.error("Falha ao baixar %s %d: %s", doc_type, year, e)
                results[year] = []
        return results

    def get_local_files(
        self,
        doc_type: str,
        year: int,
        dataset: Optional[str] = None,
    ) -> list[Path]:
        """
        Retorna arquivos já baixados sem fazer nova requisição.

        Args:
            doc_type: "DFP" ou "ITR"
            year: Ano
            dataset: Filtrar por nome de dataset (ex: "DRE_con")

        Returns:
            Lista de Paths para CSVs locais.
        """
        base = self.output_dir / doc_type / str(year)
        if not base.exists():
            return []
        files = list(base.glob("*.csv"))
        if dataset:
            files = [f for f in files if dataset.lower() in f.name.lower()]
        return files

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    def _download_and_extract(
        self,
        url: str,
        dest_dir: Path,
        label: str,
    ) -> list[Path]:
        """Baixa um ZIP e extrai os CSVs no dest_dir."""
        dest_dir.mkdir(parents=True, exist_ok=True)

        # Verificar se já foi baixado
        existing = list(dest_dir.glob("*.csv"))
        if existing:
            logger.info("[%s] Já existem %d CSVs em %s — pulando download.", label, len(existing), dest_dir)
            return existing

        logger.info("[%s] Baixando: %s", label, url)
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if response.status_code == 404:
                logger.warning("[%s] Arquivo não encontrado na CVM (404): %s", label, url)
            else:
                logger.error("[%s] Erro HTTP %d: %s", label, response.status_code, url)
            raise

        extracted: list[Path] = []
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            for name in zf.namelist():
                if not name.endswith(".csv"):
                    continue
                out_path = dest_dir / Path(name).name
                out_path.write_bytes(zf.read(name))
                extracted.append(out_path)
                logger.debug("[%s] Extraído: %s", label, out_path.name)

        logger.info("[%s] %d arquivos extraídos em %s", label, len(extracted), dest_dir)
        return extracted
