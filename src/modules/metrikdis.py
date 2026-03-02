# src/modules/metrik_dis.py
# Revision Notes (2026-03-02)
# - QDialog + loadUi kaldırıldı; tek dosyada QWidget tabanlı modül olarak yeniden yazıldı.
# - Geçersiz import (dec) ve mysql importları kaldırıldı. :contentReference[oaicite:0]{index=0}
# - DB erişimi doğrudan sqlite3.connect() ile değil, db.py üzerinden yapılır.
# - Navigasyon index bağımlı değil: go_back callback ile "← Geri".
# - Etiket standardı: anlam merkezli + birim görünür, sembol parantez içinde.
# - Hesap çekirdeği korunmuştur:
#     Dis_Alani = π (dMajMin^2 - DiMinMax^2) / 4
#     BasincEtki_Alani = π (Ic_Cap^2) / 4
#     Basinc = MEOP * S
#     Eksenel_Kuvvet = Basinc * BasincEtki_Alani
#     Tek_Dis_Gerilme = Eksenel_Kuvvet / Dis_Alani
#     2 diş: /2, 3 diş: /3

import math
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QFormLayout, QComboBox
)
from PyQt5.QtCore import Qt

from db import fetch_all, fetch_one
from utils import parse_float


class MetrikDisModule(QWidget):
    """
    Metrik diş geometrisi görüntüleme + diş arayüz alanı/gerilme hesabı.

    DB:
      - civata tablosu: seçilen Designation'a göre diş/karşı diş limitleri.
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
        title = QLabel("Metrik Diş Verileri ve Diş Gerilmesi")
        title.setStyleSheet("font-weight:700; font-size:16px;")
        header.addWidget(btn_back, 0, Qt.AlignLeft)
        header.addWidget(title, 1, Qt.AlignLeft)
        header.addStretch(1)
        root.addLayout(header)

        # --- Inputs
        gb_in = QGroupBox("Girdiler")
        form_in = QFormLayout(gb_in)
        form_in.setHorizontalSpacing(14)
        form_in.setVerticalSpacing(10)

        self.cb_designation = QComboBox()

        self.le_Basinc = QLineEdit(); self.le_Basinc.setPlaceholderText("Örn: 10")
        self.le_icCap = QLineEdit(); self.le_icCap.setPlaceholderText("Örn: 120")
        self.le_S = QLineEdit(); self.le_S.setPlaceholderText("Örn: 1.5")

        form_in.addRow("Cıvata boyutu (Designation) [–]", self.cb_designation)
        form_in.addRow("Çalışma basıncı (MEOP) [bar]*", self.le_Basinc)
        form_in.addRow("Basınç etki çapı / iç çap (D) [mm]", self.le_icCap)
        form_in.addRow("Güvenlik katsayısı (S) [–]", self.le_S)

        note = QLabel("*Not: Orijinal modülde basınç birimi dönüşümü yapılmıyor; MEOP·S doğrudan kullanılıyor.")
        note.setStyleSheet("color:#555;")
        form_in.addRow("", note)

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

        # --- DB fields (görüntüleme)
        gb_db = QGroupBox("Seçilen Cıvata Diş Limitleri (DB)")
        form_db = QFormLayout(gb_db)
        form_db.setHorizontalSpacing(14)
        form_db.setVerticalSpacing(10)

        self.le_dPMin = QLineEdit(); self.le_dPMin.setReadOnly(True)
        self.le_dPMax = QLineEdit(); self.le_dPMax.setReadOnly(True)
        self.le_dMinMax = QLineEdit(); self.le_dMinMax.setReadOnly(True)
        self.le_dMinMin = QLineEdit(); self.le_dMinMin.setReadOnly(True)
        self.le_dMajMin = QLineEdit(); self.le_dMajMin.setReadOnly(True)
        self.le_dMajMax = QLineEdit(); self.le_dMajMax.setReadOnly(True)

        self.le_DiPMin = QLineEdit(); self.le_DiPMin.setReadOnly(True)
        self.le_DiPMax = QLineEdit(); self.le_DiPMax.setReadOnly(True)
        self.le_DiMajMax = QLineEdit(); self.le_DiMajMax.setReadOnly(True)
        self.le_DiMajMin = QLineEdit(); self.le_DiMajMin.setReadOnly(True)
        self.le_DiMinMin = QLineEdit(); self.le_DiMinMin.setReadOnly(True)
        self.le_DiMinMax = QLineEdit(); self.le_DiMinMax.setReadOnly(True)

        self.le_Designation = QLineEdit(); self.le_Designation.setReadOnly(True)

        form_db.addRow("Dış diş hatve çap alt (dPMin) [mm]", self.le_dPMin)
        form_db.addRow("Dış diş hatve çap üst (dPMax) [mm]", self.le_dPMax)
        form_db.addRow("Dış diş minör çap üst (dMinMax) [mm]", self.le_dMinMax)
        form_db.addRow("Dış diş minör çap alt (dMinMin) [mm]", self.le_dMinMin)
        form_db.addRow("Dış diş majör çap alt (dMajMin) [mm]", self.le_dMajMin)
        form_db.addRow("Dış diş majör çap üst (dMajMax) [mm]", self.le_dMajMax)

        form_db.addRow("İç diş hatve çap alt (DiPMin) [mm]", self.le_DiPMin)
        form_db.addRow("İç diş hatve çap üst (DiPMax) [mm]", self.le_DiPMax)
        form_db.addRow("İç diş majör çap üst (DiMajMax) [mm]", self.le_DiMajMax)
        form_db.addRow("İç diş majör çap alt (DiMajMin) [mm]", self.le_DiMajMin)
        form_db.addRow("İç diş minör çap alt (DiMinMin) [mm]", self.le_DiMinMin)
        form_db.addRow("İç diş minör çap üst (DiMinMax) [mm]", self.le_DiMinMax)

        form_db.addRow("Seçilen boyut (Designation) [–]", self.le_Designation)

        root.addWidget(gb_db)

        # --- Results
        gb_out = QGroupBox("Sonuçlar")
        form_out = QFormLayout(gb_out)
        form_out.setHorizontalSpacing(14)
        form_out.setVerticalSpacing(10)

        self.le_A_dis = QLineEdit(); self.le_A_dis.setReadOnly(True)
        self.le_A_press = QLineEdit(); self.le_A_press.setReadOnly(True)
        self.le_F_ax = QLineEdit(); self.le_F_ax.setReadOnly(True)
        self.le_sig1 = QLineEdit(); self.le_sig1.setReadOnly(True)
        self.le_sig2 = QLineEdit(); self.le_sig2.setReadOnly(True)
        self.le_sig3 = QLineEdit(); self.le_sig3.setReadOnly(True)

        form_out.addRow("Tek diş arayüz alanı (A_thread) [mm²]", self.le_A_dis)
        form_out.addRow("Basınç etki alanı (A_press) [mm²]", self.le_A_press)
        form_out.addRow("Toplam eksenel kuvvet (F_ax) [N?]", self.le_F_ax)
        form_out.addRow("Gerilme (1 diş yük taşır) [birim?]", self.le_sig1)
        form_out.addRow("Gerilme (2 diş yük taşır) [birim?]", self.le_sig2)
        form_out.addRow("Gerilme (3 diş yük taşır) [birim?]", self.le_sig3)

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
            return

        row = fetch_one(
            "SELECT dPMin, dPMax, dMinMax, dMinMin, dMajMin, dMajMax, "
            "DiPMin, DiPMax, DiMajMax, DiMajMin, DiMinMin, DiMinMax, Designation "
            "FROM civata WHERE Designation = ?",
            (des,)
        )
        if not row:
            # clear all
            for le in (
                self.le_dPMin, self.le_dPMax, self.le_dMinMax, self.le_dMinMin, self.le_dMajMin, self.le_dMajMax,
                self.le_DiPMin, self.le_DiPMax, self.le_DiMajMax, self.le_DiMajMin, self.le_DiMinMin, self.le_DiMinMax,
                self.le_Designation
            ):
                le.clear()
            return

        self.le_dPMin.setText(str(row[0]))
        self.le_dPMax.setText(str(row[1]))
        self.le_dMinMax.setText(str(row[2]))
        self.le_dMinMin.setText(str(row[3]))
        self.le_dMajMin.setText(str(row[4]))
        self.le_dMajMax.setText(str(row[5]))

        self.le_DiPMin.setText(str(row[6]))
        self.le_DiPMax.setText(str(row[7]))
        self.le_DiMajMax.setText(str(row[8]))
        self.le_DiMajMin.setText(str(row[9]))
        self.le_DiMinMin.setText(str(row[10]))
        self.le_DiMinMax.setText(str(row[11]))
        self.le_Designation.setText(str(row[12]))

    # ---------------- Logic ----------------
    def calculate(self):
        self.lbl_err.setText("")

        if not self.le_dMajMin.text().strip() or not self.le_DiMinMax.text().strip():
            self.lbl_err.setText("Lütfen civata boyutu (Designation) seçiniz.")
            return

        if not self.le_Basinc.text().strip() or not self.le_icCap.text().strip() or not self.le_S.text().strip():
            self.lbl_err.setText("Lütfen tüm değerleri giriniz.")
            return

        try:
            dMajMin = parse_float(self.le_dMajMin.text().strip(), "dMajMin")
            DiMinMax = parse_float(self.le_DiMinMax.text().strip(), "DiMinMax")
            Ic_Cap = parse_float(self.le_icCap.text().strip(), "Çap (D)")
            MEOP = parse_float(self.le_Basinc.text().strip(), "MEOP")
            S = parse_float(self.le_S.text().strip(), "Güvenlik katsayısı (S)")
        except Exception as e:
            self.lbl_err.setText(str(e))
            return

        # Orijinal çekirdek
        Basinc = MEOP * S

        Dis_Alani = math.pi * (dMajMin * dMajMin - DiMinMax * DiMinMax) / 4.0
        if Dis_Alani <= 0:
            self.lbl_err.setText("Diş alanı (A_thread) pozitif değil. Seçilen çap limitlerini kontrol edin.")
            return

        BasincEtki_Alani = math.pi * (Ic_Cap * Ic_Cap) / 4.0
        Eksenel_Kuvvet = Basinc * BasincEtki_Alani

        Tek_Dis_Gerilme = Eksenel_Kuvvet / Dis_Alani
        Iki_Dis_Gerilme = Tek_Dis_Gerilme / 2.0
        Uc_Dis_Gerilme = Tek_Dis_Gerilme / 3.0

        self.le_A_dis.setText(f"{Dis_Alani:.2f}")
        self.le_A_press.setText(f"{BasincEtki_Alani:.2f}")
        self.le_F_ax.setText(f"{Eksenel_Kuvvet:.2f}")
        self.le_sig1.setText(f"{Tek_Dis_Gerilme:.2f}")
        self.le_sig2.setText(f"{Iki_Dis_Gerilme:.2f}")
        self.le_sig3.setText(f"{Uc_Dis_Gerilme:.2f}")
