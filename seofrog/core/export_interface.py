# seofrog/core/export_interface.py

from abc import ABC, abstractmethod
import pandas as pd

class ExporterInterface(ABC):
    @abstractmethod
    def export(self, data: list, writer: pd.ExcelWriter):
        pass

    def _create_success_sheet(self, writer: pd.ExcelWriter, message: str):
        df = pd.DataFrame([{"Status": message}])
        df.to_excel(writer, sheet_name="✅ Sem problemas detectados", index=False)
