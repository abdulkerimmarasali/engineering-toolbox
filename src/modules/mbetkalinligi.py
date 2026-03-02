# src/modules/mb_et_kalinligi.py
# Revision Notes (2026-03-02)
# - QDialog + loadUi kaldırıldı; tek dosyada QWidget tabanlı modül olarak yeniden yazıldı.
# - Geçersiz import (dec) kaldırıldı.
# - mysql/import sys gereksizleri kaldırıldı.
# - Navigasyon index bağımlı değil: go_back callback ile "← Geri".
# - Etiket standardı: anlam merkezli + birimler görünür, sembol parantez içinde.
# - Hesap çekirdeği korunmuştur:
#     tM = (MEOP*1.1*D)/(2*AKMA)
#     tK = (MEOP*S*D)/(2*CEKME)
# Kaynak: orijinal modül :contentReference[oaicite:0]{index=0}

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QFormLayout
)
from PyQt5.QtCore import Qt

from src.utils import parse_float


class MbEtKalinligiModule(QWidget):
    """
    Basınçlı Kap Gövde (Silindirik) Et Kalınlığı Hesabı.

    Girdiler:
      - Çalışma basıncı (MEOP) [bar]
      - Emniyet katsayısı (S) [–]
      - İç çap (D) [mm]
      - Akma dayanımı (σ_y) [MPa]
      - Çekme dayanımı (σ_u) [MPa]

    Çıktılar:
      - Akmaya göre et kalınlığı (t_M) [mm]
      - Patlatmaya/çekmeye göre et kalınlığı (t_K) [mm]

    Not:
      Orijinal modülde birim dönüşümü yoktur; formüller aynen korunmuştur.
    """

    def __init__(self, go_back_callback):
        super().__init__()
        self.go_back = go_back_callback
        self._build_ui()

    # ---------------- UI ----------------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        header = QHBoxLayout()
        btn_back = QPushButton("← Geri")
        btn_back.clicked.connect(self.go_back)
        title = QLabel("Basınçlı Kap Gövde Et Kalınlığı")
        title.setStyleSheet("font-weight:700; font-size:16px;")
        header.addWidget(btn_back, 0, Qt.AlignLeft)
        header.addWidget(title, 1, Qt.AlignLeft)
        header.addStretch(1)
        root.addLayout(header)

        # Inputs
        gb_in = QGroupBox("Girdiler")
        form_in = QFormLayout(gb_in)
        form_in.setHorizontalSpacing(14)
        form_in.setVerticalSpacing(10)

        self.le_MEOP = QLineEdit(); self.le_MEOP.setPlaceholderText("Örn: 10")
        self.le_S = QLineEdit(); self.le_S.setPlaceholderText("Örn: 1.5")
        self.le_D = QLineEdit(); self.le_D.setPlaceholderText("Örn: 500")
        self.le_Akma = QLineEdit(); self.le_Akma.setPlaceholderText("Örn: 250")
        self.le_Cekme = QLineEdit(); self.le_Cekme.setPlaceholderText("Örn: 450")

        form_in.addRow("Çalışma basıncı (MEOP) [bar]", self.le_MEOP)
        form_in.addRow("Emniyet katsayısı (S) [–]", self.le_S)
        form_in.addRow("İç çap (D) [mm]", self.le_D)
        form_in.addRow("Akma dayanımı (σ_y) [MPa]", self.le_Akma)
        form_in.addRow("Çekme dayanımı (σ_u) [MPa]", self.le_Cekme)

        root.addWidget(gb_in)

        # Actions + error
        act = QHBoxLayout()
        self.btn_calc = QPushButton("Hesapla")
        self.btn_calc.clicked.connect(self.calculate)
        self.lbl_err = QLabel("")
        self.lbl_err.setStyleSheet("color:#B00020; font-weight:600;")
        act.addWidget(self.btn_calc, 0, Qt.AlignLeft)
        act.addWidget(self.lbl_err, 1, Qt.AlignLeft)
        root.addLayout(act)

        # Outputs
        gb_out = QGroupBox("Sonuçlar")
        form_out = QFormLayout(gb_out)
        form_out.setHorizontalSpacing(14)
        form_out.setVerticalSpacing(10)

        self.le_tM = QLineEdit(); self.le_tM.setReadOnly(True)
        self.le_tK = QLineEdit(); self.le_tK.setReadOnly(True)

        form_out.addRow("Akmaya göre et kalınlığı (t_M) [mm]", self.le_tM)
        form_out.addRow("Patlatmaya/çekmeye göre et kalınlığı (t_K) [mm]", self.le_tK)

        note = QLabel("Not: Orijinal koddaki formül ve katsayılar korunmuştur.")
        note.setStyleSheet("color:#555;")
        form_out.addRow("", note)

        root.addWidget(gb_out)

    # ---------------- Logic ----------------
    def calculate(self):
        self.lbl_err.setText("")

        required = [
            (self.le_MEOP, "MEOP"),
            (self.le_S, "S"),
            (self.le_D, "D"),
            (self.le_Akma, "Akma"),
            (self.le_Cekme, "Çekme"),
        ]
        for le, _name in required:
            if not le.text().strip():
                self.lbl_err.setText("Lütfen tüm değerleri giriniz.")
                return

        try:
            MEOP = parse_float(self.le_MEOP.text().strip(), "Çalışma basıncı (MEOP)")
            S = parse_float(self.le_S.text().strip(), "Emniyet katsayısı (S)")
            D = parse_float(self.le_D.text().strip(), "İç çap (D)")
            AKMA = parse_float(self.le_Akma.text().strip(), "Akma dayanımı (σ_y)")
            CEKME = parse_float(self.le_Cekme.text().strip(), "Çekme dayanımı (σ_u)")
        except Exception as e:
            self.lbl_err.setText(str(e))
            return

        denom_M = 2.0 * AKMA
        denom_K = 2.0 * CEKME

        if denom_M == 0 or denom_K == 0:
            self.lbl_err.setText("Akma/Çekme dayanımı sıfır olamaz.")
            return

        # Orijinal çekirdek
        tM = (MEOP * 1.1 * D) / denom_M
        tK = (MEOP * S * D) / denom_K

        self.le_tM.setText(f"{tM:.3f}")
        self.le_tK.setText(f"{tK:.3f}")
