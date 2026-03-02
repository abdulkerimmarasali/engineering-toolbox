# src/modules/alin_conta_civata_sayisi.py
# Revision Notes (2026-03-02)
# - QDialog + loadUi kaldırıldı; tek dosyada QWidget tabanlı modül olarak yeniden yazıldı.
# - Geçersiz import (dec) ve mysql importu kaldırıldı.
# - Navigasyon index bağımlı değil: go_back callback ile "← Geri".
# - Etiket standardı: anlam merkezli + birimler görünür, sembol parantez içinde.
# - Hesap çekirdeği korunmuştur:
#     n = (2*pi*r) / ( (2*t*tan(pi/6)) + Dpul )
# Kaynak: orijinal modül :contentReference[oaicite:0]{index=0}

import math
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QFormLayout
)
from PyQt5.QtCore import Qt

from utils import parse_float


class AlinContaCivataSayisiModule(QWidget):
    """
    Alın Conta - Cıvata Sayısı Hesabı

    Girdiler:
      - Pul çapı (D_pul) [mm]
      - Et kalınlığı / yükseklik parametresi (t) [mm]
      - Hat yarıçapı (r) [mm]

    Çıktı:
      - Hesaplanan cıvata adedi (n) [–]

    Hesap:
      n = (2*pi*r) / ( (2*t*tan(pi/6)) + D_pul )
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
        title = QLabel("Alın Conta – Cıvata Sayısı")
        title.setStyleSheet("font-weight:700; font-size:16px;")
        header.addWidget(btn_back, 0, Qt.AlignLeft)
        header.addWidget(title, 1, Qt.AlignLeft)
        header.addStretch(1)
        root.addLayout(header)

        gb_in = QGroupBox("Girdiler")
        form = QFormLayout(gb_in)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(10)

        self.le_Dpul = QLineEdit()
        self.le_Dpul.setPlaceholderText("Örn: 18.0")

        self.le_t = QLineEdit()
        self.le_t.setPlaceholderText("Örn: 3.0")

        self.le_r = QLineEdit()
        self.le_r.setPlaceholderText("Örn: 60.0")

        form.addRow("Pul çapı (D_pul) [mm]", self.le_Dpul)
        form.addRow("Et kalınlığı / geometri parametresi (t) [mm]", self.le_t)
        form.addRow("Cıvata hat yarıçapı (r) [mm]", self.le_r)

        root.addWidget(gb_in)

        actions = QHBoxLayout()
        self.btn_calc = QPushButton("Hesapla")
        self.btn_calc.clicked.connect(self.calculate)
        self.lbl_err = QLabel("")
        self.lbl_err.setStyleSheet("color:#B00020; font-weight:600;")
        actions.addWidget(self.btn_calc, 0, Qt.AlignLeft)
        actions.addWidget(self.lbl_err, 1, Qt.AlignLeft)
        root.addLayout(actions)

        gb_out = QGroupBox("Sonuçlar")
        form_out = QFormLayout(gb_out)
        form_out.setHorizontalSpacing(14)
        form_out.setVerticalSpacing(10)

        self.le_n = QLineEdit()
        self.le_n.setReadOnly(True)

        form_out.addRow("Hesaplanan cıvata adedi (n) [–]", self.le_n)
        root.addWidget(gb_out)

    # ---------------- Logic ----------------
    def calculate(self):
        self.lbl_err.setText("")

        if not self.le_Dpul.text().strip() or not self.le_t.text().strip() or not self.le_r.text().strip():
            self.lbl_err.setText("Lütfen tüm değerleri giriniz.")
            return

        try:
            Dpul = parse_float(self.le_Dpul.text().strip(), "Pul çapı (D_pul)")
            t = parse_float(self.le_t.text().strip(), "Et kalınlığı (t)")
            r = parse_float(self.le_r.text().strip(), "Yarıçap (r)")
        except Exception as e:
            self.lbl_err.setText(str(e))
            return

        denom = (2.0 * t * math.tan(math.pi / 6.0)) + Dpul
        if denom <= 0:
            self.lbl_err.setText("Payda (2*t*tan(pi/6) + D_pul) pozitif olmalıdır.")
            return

        n = (2.0 * math.pi * r) / denom
        self.le_n.setText(f"{n:.1f}")
