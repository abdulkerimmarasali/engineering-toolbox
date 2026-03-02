# src/modules/civata_sayisi.py
# Revision Notes (2026-03-02)
# - QDialog + loadUi kaldırıldı; tek dosyada QWidget tabanlı modül olarak yeniden yazıldı.
# - Geçersiz import (dec) ve mysql importları kaldırıldı.
# - DB erişimi doğrudan sqlite3.connect() ile değil, db.py üzerinden yapılır.
# - Navigasyon index bağımlı değil: go_back callback ile "← Geri".
# - Etiket standardı: anlam merkezli + birim görünür, sembol parantez içinde.
# - Hesap çekirdeği korunmuştur (diş alanı, basınç etki alanı, eksenel kuvvet, 1/2/3 diş yük paylaşımı gerilmeleri).
# Kaynak: orijinal modül :contentReference[oaicite:0]{index=0}

import math
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QFormLayout, QComboBox
)
from PyQt5.QtCore import Qt

from src.db import fetch_all, fetch_one
from src.utils import parse_float


class CivataSayisiModule(QWidget):
    """
    Metrik cıvata / diş arayüz gerilmesi (1/2/3 diş yük paylaşımı) hesabı.

    DB:
      - civata: Designation'a göre dMajMin, DiMinMax vb. alanlar
      - metrik_standart_dis_adimlari: Dis -> Adim

    Hesap (orijinal):
      Dis_Alani = π (dMajMin^2 - DiMinMax^2) / 4
      BasincEtki_Alani = π (Ic_Cap^2) / 4
      Basinc = MEOP * S
      Eksenel_Kuvvet = Basinc * BasincEtki_Alani
      Tek_Dis_Gerilme = (Eksenel_Kuvvet / Civata_Sayisi) / Dis_Alani
      Iki_Dis_Gerilme = Tek_Dis_Gerilme / 2
      Uc_Dis_Gerilme  = Tek_Dis_Gerilme / 3
    """

    def __init__(self, go_back_callback):
        super().__init__()
        self.go_back = go_back_callback
        self._build_ui()
        self._load_options()

    # ---------------- UI ----------------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        header = QHBoxLayout()
        btn_back = QPushButton("← Geri")
        btn_back.clicked.connect(self.go_back)
        title = QLabel("Metrik Cıvata Sayısı / Diş Gerilmesi")
        title.setStyleSheet("font-weight:700; font-size:16px;")
        header.addWidget(btn_back, 0, Qt.AlignLeft)
        header.addWidget(title, 1, Qt.AlignLeft)
        header.addStretch(1)
        root.addLayout(header)

        # --- Inputs card
        gb_in = QGroupBox("Girdiler")
        form_in = QFormLayout(gb_in)
        form_in.setHorizontalSpacing(14)
        form_in.setVerticalSpacing(10)

        self.cb_designation = QComboBox()
        self.cb_standart_dis = QComboBox()

        self.le_bolt_count = QLineEdit()
        self.le_bolt_count.setPlaceholderText("Örn: 8")

        self.le_meop = QLineEdit()
        self.le_meop.setPlaceholderText("Örn: 10")

        self.le_id = QLineEdit()
        self.le_id.setPlaceholderText("Örn: 120")

        self.le_sf = QLineEdit()
        self.le_sf.setPlaceholderText("Örn: 1.5")

        form_in.addRow("Cıvata boyutu (Designation) [–]", self.cb_designation)
        form_in.addRow("Standart diş (Dis) [–]", self.cb_standart_dis)
        form_in.addRow("Cıvata sayısı (n) [adet]", self.le_bolt_count)
        form_in.addRow("Çalışma basıncı (MEOP) [bar]*", self.le_meop)
        form_in.addRow("Basınç etki çapı / iç çap (D) [mm]", self.le_id)
        form_in.addRow("Güvenlik katsayısı (S) [–]", self.le_sf)

        note = QLabel("*Not: Orijinal kodda basınç birimi dönüştürülmüyor; MEOP·S doğrudan kullanılıyor.")
        note.setStyleSheet("color:#555;")
        form_in.addRow("", note)

        root.addWidget(gb_in)

        # Actions
        actions = QHBoxLayout()
        self.btn_calc = QPushButton("Hesapla")
        self.btn_calc.clicked.connect(self.calculate)
        self.lbl_err = QLabel("")
        self.lbl_err.setStyleSheet("color:#B00020; font-weight:600;")
        actions.addWidget(self.btn_calc, 0, Qt.AlignLeft)
        actions.addWidget(self.lbl_err, 1, Qt.AlignLeft)
        root.addLayout(actions)

        # --- Reference card (DB’den gelen değerler)
        gb_ref = QGroupBox("Seçilen Cıvata Verileri (DB)")
        form_ref = QFormLayout(gb_ref)
        form_ref.setHorizontalSpacing(14)
        form_ref.setVerticalSpacing(10)

        self.le_dMajMin = QLineEdit(); self.le_dMajMin.setReadOnly(True)
        self.le_DiMinMax = QLineEdit(); self.le_DiMinMax.setReadOnly(True)
        self.le_pitch = QLineEdit(); self.le_pitch.setReadOnly(True)

        form_ref.addRow("Dış diş majör çap alt sınır (dMajMin) [mm]", self.le_dMajMin)
        form_ref.addRow("İç diş minör çap üst sınır (DiMinMax) [mm]", self.le_DiMinMax)
        form_ref.addRow("Standart adım (P) [mm]", self.le_pitch)

        root.addWidget(gb_ref)

        # --- Results card
        gb_out = QGroupBox("Sonuçlar")
        form_out = QFormLayout(gb_out)
        form_out.setHorizontalSpacing(14)
        form_out.setVerticalSpacing(10)

        self.le_area_thread = QLineEdit(); self.le_area_thread.setReadOnly(True)
        self.le_area_press = QLineEdit(); self.le_area_press.setReadOnly(True)
        self.le_force_ax = QLineEdit(); self.le_force_ax.setReadOnly(True)

        self.le_sigma_1 = QLineEdit(); self.le_sigma_1.setReadOnly(True)
        self.le_sigma_2 = QLineEdit(); self.le_sigma_2.setReadOnly(True)
        self.le_sigma_3 = QLineEdit(); self.le_sigma_3.setReadOnly(True)

        form_out.addRow("Tek diş arayüz alanı (A_thread) [mm²]", self.le_area_thread)
        form_out.addRow("Basınç etki alanı (A_press) [mm²]", self.le_area_press)
        form_out.addRow("Toplam eksenel kuvvet (F_ax) [N?]", self.le_force_ax)
        form_out.addRow("Gerilme (1 diş yük taşır) [birim?]", self.le_sigma_1)
        form_out.addRow("Gerilme (2 diş yük taşır) [birim?]", self.le_sigma_2)
        form_out.addRow("Gerilme (3 diş yük taşır) [birim?]", self.le_sigma_3)

        unit_note = QLabel("Not: Orijinal kodda basınç/kuvvet birim dönüşümü yapılmadığı için çıktı birimleri girişle tutarlıdır.")
        unit_note.setStyleSheet("color:#555;")
        form_out.addRow("", unit_note)

        root.addWidget(gb_out)

        # Signals (tek sefer)
        self.cb_designation.currentTextChanged.connect(self._on_selection_changed)
        self.cb_standart_dis.currentTextChanged.connect(self._on_selection_changed)

    # ---------------- DB loading ----------------
    def _load_options(self):
        self.cb_designation.blockSignals(True)
        self.cb_standart_dis.blockSignals(True)

        self.cb_designation.clear()
        self.cb_standart_dis.clear()

        # Designation list
        rows = fetch_all("SELECT Designation FROM civata")
        for r in rows:
            if r and r[0] is not None:
                self.cb_designation.addItem(str(r[0]))

        # Standart Dis list
        rows2 = fetch_all("SELECT Dis FROM metrik_standart_dis_adimlari")
        for r in rows2:
            if r and r[0] is not None:
                self.cb_standart_dis.addItem(str(r[0]))

        self.cb_designation.blockSignals(False)
        self.cb_standart_dis.blockSignals(False)

        self._on_selection_changed()

    def _on_selection_changed(self):
        self.lbl_err.setText("")

        des = self.cb_designation.currentText().strip()
        dis = self.cb_standart_dis.currentText().strip()

        # civata record
        if des:
            row = fetch_one(
                "SELECT dMajMin, DiMinMax FROM civata WHERE Designation = ?",
                (des,)
            )
            if row:
                self.le_dMajMin.setText(str(row[0]))
                self.le_DiMinMax.setText(str(row[1]))
            else:
                self.le_dMajMin.clear()
                self.le_DiMinMax.clear()

        # pitch record
        if dis:
            row2 = fetch_one(
                "SELECT Adim FROM metrik_standart_dis_adimlari WHERE Dis = ?",
                (dis,)
            )
            if row2:
                self.le_pitch.setText(str(row2[0]))
            else:
                self.le_pitch.clear()

    # ---------------- Calculation ----------------
    def calculate(self):
        self.lbl_err.setText("")

        # Seçim kontrolü
        if not self.le_dMajMin.text().strip() or not self.le_DiMinMax.text().strip():
            self.lbl_err.setText("Lütfen civata boyutu (Designation) seçiniz.")
            return

        # Zorunlu girişler
        required = [
            (self.le_bolt_count, "Cıvata sayısı (n)"),
            (self.le_meop, "Çalışma basıncı (MEOP)"),
            (self.le_id, "Basınç etki çapı / iç çap (D)"),
            (self.le_sf, "Güvenlik katsayısı (S)"),
        ]
        for le, name in required:
            if not le.text().strip():
                self.lbl_err.setText("Lütfen tüm değerleri giriniz.")
                return

        try:
            n_bolt = parse_float(self.le_bolt_count.text().strip(), "Cıvata sayısı (n)")
            meop = parse_float(self.le_meop.text().strip(), "MEOP")
            D = parse_float(self.le_id.text().strip(), "Çap (D)")
            S = parse_float(self.le_sf.text().strip(), "Güvenlik katsayısı (S)")

            dMajMin = parse_float(self.le_dMajMin.text().strip(), "dMajMin")
            DiMinMax = parse_float(self.le_DiMinMax.text().strip(), "DiMinMax")
        except Exception as e:
            self.lbl_err.setText(str(e))
            return

        if n_bolt <= 0:
            self.lbl_err.setText("Cıvata sayısı (n) pozitif olmalıdır.")
            return
        if D <= 0:
            self.lbl_err.setText("Çap (D) pozitif olmalıdır.")
            return

        # Orijinal: Basinc = MEOP * S
        basinc = meop * S

        # Tek Diş Arayüz Alanı
        A_thread = (math.pi) * (dMajMin * dMajMin - DiMinMax * DiMinMax) / 4.0

        if A_thread <= 0:
            self.lbl_err.setText("Hesaplanan diş alanı (A_thread) pozitif değil. Seçilen çap değerlerini kontrol edin.")
            return

        # Basınç Etki Alanı
        A_press = (math.pi) * (D * D) / 4.0

        # Toplam Eksenel Kuvvet
        F_ax = basinc * A_press

        # Gerilmeler
        sigma_1 = (F_ax / n_bolt) / A_thread
        sigma_2 = sigma_1 / 2.0
        sigma_3 = sigma_1 / 3.0

        # Yazdır
        self.le_area_thread.setText(f"{A_thread:.2f}")
        self.le_area_press.setText(f"{A_press:.2f}")
        self.le_force_ax.setText(f"{F_ax:.2f}")
        self.le_sigma_1.setText(f"{sigma_1:.2f}")
        self.le_sigma_2.setText(f"{sigma_2:.2f}")
        self.le_sigma_3.setText(f"{sigma_3:.2f}")
