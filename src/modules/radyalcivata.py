# src/modules/radyal_civata_sayisi.py
# Revision Notes (2026-03-02)
# - QDialog + loadUi kaldırıldı; tek dosyada QWidget tabanlı modül olarak yeniden yazıldı.
# - Geçersiz import (dec) ve mysql importları kaldırıldı. :contentReference[oaicite:0]{index=0}
# - DB erişimi doğrudan sqlite3.connect() ile değil, db.py üzerinden yapılır.
# - Navigasyon index bağımlı değil: go_back callback ile "← Geri".
# - Etiket standardı: anlam merkezli + birimler görünür, sembol parantez içinde.
# - Hesap çekirdeği korunmuştur:
#     Kesit_Alani = π*dMinMin^2/4
#     BasincEtki_Alani = π*D^2/4
#     Basinc = MEOP*S
#     Radyal_Kuvvet = Basinc*BasincEtki_Alani
#     Tek_Civata_Kesme = Radyal_Kuvvet/n
#     Kesme_Stresi = Tek_Civata_Kesme/Kesit_Alani

import math
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QFormLayout, QComboBox
)
from PyQt5.QtCore import Qt

from db import fetch_all, fetch_one
from utils import parse_float


class RadyalCivataSayisiModule(QWidget):
    """
    Radyal Cıvata Sayısı / Kesme Gerilmesi hesabı.

    Girdiler:
      - Cıvata boyutu (Designation) [–] (DB)
      - Cıvata sayısı (n) [adet]
      - Çalışma basıncı (MEOP) [bar]
      - Basınç etki çapı / iç çap (D) [mm]
      - Güvenlik katsayısı (S) [–]

    DB'den:
      - Dış diş minör çap alt sınır (dMinMin) [mm] -> kesit alanı için kullanılır.

    Çıktılar:
      - Cıvata kesit alanı (A_bolt) [mm²]
      - Basınç etki alanı (A_press) [mm²]
      - Toplam radyal kuvvet (F_rad) [N?]
      - Tek civata kesme kuvveti (F_shear,1) [N?]
      - Kesme gerilmesi (τ) [birim?]
    """

    def __init__(self, go_back_callback):
        super().__init__()
        self.go_back = go_back_callback
        self._build_ui()
        self._load_designations()

    # ---------------- UI ----------------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        header = QHBoxLayout()
        btn_back = QPushButton("← Geri")
        btn_back.clicked.connect(self.go_back)
        title = QLabel("Radyal Cıvata Sayısı / Kesme Gerilmesi")
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

        self.cb_designation = QComboBox()

        self.le_n = QLineEdit(); self.le_n.setPlaceholderText("Örn: 8")
        self.le_MEOP = QLineEdit(); self.le_MEOP.setPlaceholderText("Örn: 10")
        self.le_D = QLineEdit(); self.le_D.setPlaceholderText("Örn: 120")
        self.le_S = QLineEdit(); self.le_S.setPlaceholderText("Örn: 1.5")

        form_in.addRow("Cıvata boyutu (Designation) [–]", self.cb_designation)
        form_in.addRow("Cıvata sayısı (n) [adet]", self.le_n)
        form_in.addRow("Çalışma basıncı (MEOP) [bar]*", self.le_MEOP)
        form_in.addRow("Basınç etki çapı / iç çap (D) [mm]", self.le_D)
        form_in.addRow("Güvenlik katsayısı (S) [–]", self.le_S)

        note = QLabel("*Not: Orijinal modülde basınç birimi dönüştürülmüyor; MEOP·S doğrudan kullanılıyor.")
        note.setStyleSheet("color:#555;")
        form_in.addRow("", note)

        root.addWidget(gb_in)

        # Action + error
        act = QHBoxLayout()
        self.btn_calc = QPushButton("Hesapla")
        self.btn_calc.clicked.connect(self.calculate)
        self.lbl_err = QLabel("")
        self.lbl_err.setStyleSheet("color:#B00020; font-weight:600;")
        act.addWidget(self.btn_calc, 0, Qt.AlignLeft)
        act.addWidget(self.lbl_err, 1, Qt.AlignLeft)
        root.addLayout(act)

        # DB data card
        gb_db = QGroupBox("Seçilen Cıvata Verileri (DB)")
        form_db = QFormLayout(gb_db)
        form_db.setHorizontalSpacing(14)
        form_db.setVerticalSpacing(10)

        self.le_dMinMin = QLineEdit(); self.le_dMinMin.setReadOnly(True)
        self.le_Designation = QLineEdit(); self.le_Designation.setReadOnly(True)

        form_db.addRow("Dış diş minör çap alt sınır (dMinMin) [mm]", self.le_dMinMin)
        form_db.addRow("Seçilen boyut (Designation) [–]", self.le_Designation)
        root.addWidget(gb_db)

        # Results
        gb_out = QGroupBox("Sonuçlar")
        form_out = QFormLayout(gb_out)
        form_out.setHorizontalSpacing(14)
        form_out.setVerticalSpacing(10)

        self.le_A_bolt = QLineEdit(); self.le_A_bolt.setReadOnly(True)
        self.le_A_press = QLineEdit(); self.le_A_press.setReadOnly(True)
        self.le_F_rad = QLineEdit(); self.le_F_rad.setReadOnly(True)
        self.le_F_shear1 = QLineEdit(); self.le_F_shear1.setReadOnly(True)
        self.le_tau = QLineEdit(); self.le_tau.setReadOnly(True)

        form_out.addRow("Cıvata kesit alanı (A_bolt) [mm²]", self.le_A_bolt)
        form_out.addRow("Basınç etki alanı (A_press) [mm²]", self.le_A_press)
        form_out.addRow("Toplam radyal kuvvet (F_rad) [N?]", self.le_F_rad)
        form_out.addRow("Tek civata kesme kuvveti (F_shear,1) [N?]", self.le_F_shear1)
        form_out.addRow("Kesme gerilmesi (τ) [birim?]", self.le_tau)

        unit_note = QLabel("Not: Orijinal kodda birim dönüşümü yapılmadığı için çıktı birimleri girişle tutarlıdır.")
        unit_note.setStyleSheet("color:#555;")
        form_out.addRow("", unit_note)

        root.addWidget(gb_out)

        # Signals
        self.cb_designation.currentTextChanged.connect(self._on_designation_changed)

    # ---------------- DB ----------------
    def _load_designations(self):
        self.cb_designation.blockSignals(True)
        self.cb_designation.clear()

        rows = fetch_all("SELECT Designation FROM civata")
        for r in rows:
            if r and r[0] is not None:
                self.cb_designation.addItem(str(r[0]))

        self.cb_designation.blockSignals(False)

        if self.cb_designation.count() > 0:
            self._on_designation_changed(self.cb_designation.currentText())

    def _on_designation_changed(self, _text):
        des = self.cb_designation.currentText().strip()
        if not des:
            self.le_dMinMin.clear()
            self.le_Designation.clear()
            return

        row = fetch_one(
            "SELECT dMinMin, Designation FROM civata WHERE Designation = ?",
            (des,)
        )
        if not row:
            self.le_dMinMin.clear()
            self.le_Designation.clear()
            return

        self.le_dMinMin.setText(str(row[0]))
        self.le_Designation.setText(str(row[1]))

    # ---------------- Logic ----------------
    def calculate(self):
        self.lbl_err.setText("")

        if not self.le_dMinMin.text().strip():
            self.lbl_err.setText("Lütfen civata boyutu (Designation) seçiniz.")
            return

        required = [
            (self.le_n, "Cıvata sayısı (n)"),
            (self.le_MEOP, "MEOP"),
            (self.le_D, "Çap (D)"),
            (self.le_S, "Güvenlik katsayısı (S)"),
        ]
        for le, _name in required:
            if not le.text().strip():
                self.lbl_err.setText("Lütfen tüm değerleri giriniz.")
                return

        try:
            n = parse_float(self.le_n.text().strip(), "Cıvata sayısı (n)")
            MEOP = parse_float(self.le_MEOP.text().strip(), "Çalışma basıncı (MEOP)")
            D = parse_float(self.le_D.text().strip(), "Basınç etki çapı (D)")
            S = parse_float(self.le_S.text().strip(), "Güvenlik katsayısı (S)")
            dMinMin = parse_float(self.le_dMinMin.text().strip(), "dMinMin")
        except Exception as e:
            self.lbl_err.setText(str(e))
            return

        if n <= 0:
            self.lbl_err.setText("Cıvata sayısı (n) pozitif olmalıdır.")
            return
        if D <= 0:
            self.lbl_err.setText("Çap (D) pozitif olmalıdır.")
            return
        if dMinMin <= 0:
            self.lbl_err.setText("dMinMin pozitif olmalıdır.")
            return

        # Orijinal çekirdek
        A_bolt = math.pi * (dMinMin * dMinMin) / 4.0
        A_press = math.pi * (D * D) / 4.0
        Basinc = MEOP * S
        F_rad = Basinc * A_press
        F_shear1 = F_rad / n
        tau = F_shear1 / A_bolt

        self.le_A_bolt.setText(f"{A_bolt:.2f}")
        self.le_A_press.setText(f"{A_press:.2f}")
        self.le_F_rad.setText(f"{F_rad:.2f}")
        self.le_F_shear1.setText(f"{F_shear1:.2f}")
        self.le_tau.setText(f"{tau:.2f}")
