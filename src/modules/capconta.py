# src/modules/cap_conta.py
# Revision Notes (2026-03-02)
# - QDialog + loadUi kaldırıldı; tek dosyada QWidget tabanlı modül olarak yeniden yazıldı.
# - Geçersiz import (dec) ve mysql importları kaldırıldı.
# - Navigasyon index bağımlı değil: go_back callback ile "← Geri".
# - DB erişimi doğrudan sqlite3.connect() ile değil, db.py üzerinden yapılır.
# - Etiket standardı: anlam merkezli + birimler görünür, sembol parantez içinde.
# - Hesap çekirdeği korunmuştur (yuva derinliği min/max, kesit min/max, germe düzeltmesi,
#   squeeze Smax/Smin ve germe oranı kriterleri).
# Kaynak: orijinal modül :contentReference[oaicite:0]{index=0}

import math
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QFormLayout, QComboBox
)
from PyQt5.QtCore import Qt

from src.db import fetch_all, fetch_one
from src.utils import parse_float


class CapContaModule(QWidget):
    """
    Çap Conta (O-Ring) hesabı

    Girdiler:
      - O-ring kesit çapı (W) [mm] (DB'den)
      - O-ring iç çapı (DI) [mm] (W'ye bağlı DB tablosundan)
      - Kanal çapları: D1_min, D1_max, D2_min, D2_max [mm]

    Çıktılar (orijinal modülle aynı):
      - Yuva derinliği max/min:
          YUVDER_MAX = (D1_max - D2_min)/2
          YUVDER_MIN = (D1_min - D2_max)/2
      - Conta kesit max/min:
          CONKES_MAX = W + tol
          CONKES_MIN = W - tol
      - Yuvadaki etkin kesit (germe düzeltmesi):
          YUVICCONKES_MAX = CONKES_MAX * sqrt(DI / D2_min)
          YUVICCONKES_MIN = CONKES_MIN * sqrt(DI / D2_max)
      - Sıkışma:
          SIKISMA_MAX = (YUVICCONKES_MAX - YUVDER_MIN) / YUVICCONKES_MAX * 100
          SIKISMA_MIN = (YUVICCONKES_MIN - YUVDER_MAX) / YUVICCONKES_MIN * 100
      - Germe oranı (orijinal koddaki tanım):
          GERILME_ORANI = DI / D2_min
      - Kriterler:
          Squeeze: 10–30 %
          Germe oranı: 0.95–1.00
    """

    def __init__(self, go_back_callback):
        super().__init__()
        self.go_back = go_back_callback

        # W -> (DI tablo adı, tol)
        # (Mevcut koddaki tol değerleri korunmuştur.)
        self._W_RULES = {
            1.78: ("oring_w_178", 0.08),
            2.62: ("oring_w_262", 0.08),
            3.53: ("oring_w_353", 0.10),
            5.33: ("oring_w_533", 0.13),
            6.99: ("oring_w_699", 0.15),
        }

        self._build_ui()
        self._load_W_options()

    # ---------------- UI ----------------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        header = QHBoxLayout()
        btn_back = QPushButton("← Geri")
        btn_back.clicked.connect(self.go_back)
        title = QLabel("Çap Conta Hesabı (O-Ring)")
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

        self.cb_W = QComboBox()
        self.cb_DI = QComboBox()
        self.cb_DI.setEnabled(False)

        self.le_DE = QLineEdit()
        self.le_DE.setReadOnly(True)

        self.le_D1min = QLineEdit(); self.le_D1min.setPlaceholderText("Örn: 50.00")
        self.le_D1max = QLineEdit(); self.le_D1max.setPlaceholderText("Örn: 50.10")
        self.le_D2min = QLineEdit(); self.le_D2min.setPlaceholderText("Örn: 45.00")
        self.le_D2max = QLineEdit(); self.le_D2max.setPlaceholderText("Örn: 45.10")

        form_in.addRow("O-ring kesit çapı (W) [mm]", self.cb_W)
        form_in.addRow("O-ring iç çapı (DI) [mm]", self.cb_DI)
        form_in.addRow("Hesaplanan dış çap (DE = DI + 2W) [mm]", self.le_DE)
        form_in.addRow("Kanal dış çap alt sınırı (D1_min) [mm]", self.le_D1min)
        form_in.addRow("Kanal dış çap üst sınırı (D1_max) [mm]", self.le_D1max)
        form_in.addRow("Kanal iç çap alt sınırı (D2_min) [mm]", self.le_D2min)
        form_in.addRow("Kanal iç çap üst sınırı (D2_max) [mm]", self.le_D2max)

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

        # Results
        gb_out = QGroupBox("Sonuçlar")
        form_out = QFormLayout(gb_out)
        form_out.setHorizontalSpacing(14)
        form_out.setVerticalSpacing(10)

        self.le_YuvDer_Max = QLineEdit(); self.le_YuvDer_Max.setReadOnly(True)
        self.le_YuvDer_Min = QLineEdit(); self.le_YuvDer_Min.setReadOnly(True)

        self.le_ConKes_Max = QLineEdit(); self.le_ConKes_Max.setReadOnly(True)
        self.le_ConKes_Min = QLineEdit(); self.le_ConKes_Min.setReadOnly(True)

        self.le_YuvicConKes_Max = QLineEdit(); self.le_YuvicConKes_Max.setReadOnly(True)
        self.le_YuvicConKes_Min = QLineEdit(); self.le_YuvicConKes_Min.setReadOnly(True)

        self.le_S_Max = QLineEdit(); self.le_S_Max.setReadOnly(True)
        self.le_S_Min = QLineEdit(); self.le_S_Min.setReadOnly(True)

        self.le_Ger = QLineEdit(); self.le_Ger.setReadOnly(True)

        self.badge_Smax = QLabel(""); self._set_badge(self.badge_Smax, None)
        self.badge_Smin = QLabel(""); self._set_badge(self.badge_Smin, None)
        self.badge_Ger = QLabel(""); self._set_badge(self.badge_Ger, None)

        self.lbl_GerNot = QLabel("")
        self.lbl_GerNot.setStyleSheet("color:#303030;")

        row_smax = QHBoxLayout()
        row_smax.addWidget(self.le_S_Max, 1)
        row_smax.addWidget(self.badge_Smax, 0)

        row_smin = QHBoxLayout()
        row_smin.addWidget(self.le_S_Min, 1)
        row_smin.addWidget(self.badge_Smin, 0)

        row_ger = QHBoxLayout()
        row_ger.addWidget(self.le_Ger, 1)
        row_ger.addWidget(self.badge_Ger, 0)

        form_out.addRow("Yuva derinliği üst sınır (h_max) [mm]", self.le_YuvDer_Max)
        form_out.addRow("Yuva derinliği alt sınır (h_min) [mm]", self.le_YuvDer_Min)
        form_out.addRow("Conta kesit üst sınır (W_max) [mm]", self.le_ConKes_Max)
        form_out.addRow("Conta kesit alt sınır (W_min) [mm]", self.le_ConKes_Min)
        form_out.addRow("Yuvadaki etkin kesit üst (W_eff,max) [mm]", self.le_YuvicConKes_Max)
        form_out.addRow("Yuvadaki etkin kesit alt (W_eff,min) [mm]", self.le_YuvicConKes_Min)
        form_out.addRow("Hesaplanan sıkışma (S_max) [%]", row_smax)
        form_out.addRow("Hesaplanan sıkışma (S_min) [%]", row_smin)
        form_out.addRow("Germe oranı (DI / D2_min) [–]", row_ger)
        form_out.addRow("", self.lbl_GerNot)

        root.addWidget(gb_out)

        # Signals (tek sefer)
        self.cb_W.currentTextChanged.connect(self._on_W_changed)
        self.cb_DI.currentTextChanged.connect(self._on_DI_changed)

    def _set_badge(self, lbl: QLabel, ok: bool | None):
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setFixedWidth(110)
        lbl.setFixedHeight(26)
        lbl.setStyleSheet("border-radius:6px; font-weight:700;")
        if ok is None:
            lbl.setText("")
            lbl.setStyleSheet("background-color:#E0E0E0; color:#303030; border-radius:6px; font-weight:700;")
        elif ok:
            lbl.setText("UYGUN")
            lbl.setStyleSheet("background-color:#2E7D32; color:white; border-radius:6px; font-weight:700;")
        else:
            lbl.setText("UYGUN DEĞİL")
            lbl.setStyleSheet("background-color:#C62828; color:white; border-radius:6px; font-weight:700;")

    # ---------------- DB Loading ----------------
    def _load_W_options(self):
        self.cb_W.blockSignals(True)
        self.cb_W.clear()

        rows = fetch_all("SELECT W FROM oring_W_tol")
        w_list = []
        for r in rows:
            try:
                w_list.append(float(r[0]))
            except Exception:
                continue

        if not w_list:
            w_list = sorted(self._W_RULES.keys())

        for w in sorted(set(w_list)):
            self.cb_W.addItem(f"{w:.2f}", w)

        self.cb_W.blockSignals(False)

        if self.cb_W.count() > 0:
            self._on_W_changed(self.cb_W.currentText())

    def _load_DI_options(self, W: float):
        self.cb_DI.blockSignals(True)
        self.cb_DI.clear()

        table, _tol = self._W_RULES.get(W, (None, None))
        if not table:
            self.cb_DI.setEnabled(False)
            self.cb_DI.blockSignals(False)
            return

        rows = fetch_all(f"SELECT DI FROM {table}")
        di_list = []
        for r in rows:
            try:
                di_list.append(float(r[0]))
            except Exception:
                continue

        for di in di_list:
            self.cb_DI.addItem(f"{di:.2f}", di)

        self.cb_DI.setEnabled(self.cb_DI.count() > 0)
        self.cb_DI.blockSignals(False)

        if self.cb_DI.count() > 0:
            self._on_DI_changed(self.cb_DI.currentText())

    # ---------------- Live Updates ----------------
    def _on_W_changed(self, _text):
        W = self.cb_W.currentData()
        if W is None:
            self.cb_DI.setEnabled(False)
            return
        self._load_DI_options(float(W))

    def _on_DI_changed(self, _text):
        W = self.cb_W.currentData()
        DI = self.cb_DI.currentData()
        if W is None or DI is None:
            self.le_DE.clear()
            return
        DE = float(DI) + 2.0 * float(W)
        self.le_DE.setText(f"{DE:.3f}")

    # ---------------- Calculation ----------------
    def calculate(self):
        self.lbl_err.setText("")
        self.lbl_GerNot.setText("")
        self._set_badge(self.badge_Smax, None)
        self._set_badge(self.badge_Smin, None)
        self._set_badge(self.badge_Ger, None)

        W = self.cb_W.currentData()
        DI = self.cb_DI.currentData()
        if W is None:
            self.lbl_err.setText("Kesit çapı (W) seçiniz.")
            return
        if DI is None:
            self.lbl_err.setText("İç çap (DI) seçiniz.")
            return

        # Zorunlu kanal çapları
        fields = [
            (self.le_D1min, "D1_min"),
            (self.le_D1max, "D1_max"),
            (self.le_D2min, "D2_min"),
            (self.le_D2max, "D2_max"),
        ]
        for le, name in fields:
            if not le.text().strip():
                self.lbl_err.setText("Lütfen tüm kanal çaplarını giriniz (D1_min, D1_max, D2_min, D2_max).")
                return

        try:
            D1_min = parse_float(self.le_D1min.text().strip(), "D1_min")
            D1_max = parse_float(self.le_D1max.text().strip(), "D1_max")
            D2_min = parse_float(self.le_D2min.text().strip(), "D2_min")
            D2_max = parse_float(self.le_D2max.text().strip(), "D2_max")
        except Exception as e:
            self.lbl_err.setText(str(e))
            return

        W = float(W)
        DI = float(DI)

        # Tol (orijinal)
        _table, tol = self._W_RULES.get(W, (None, None))
        if tol is None:
            self.lbl_err.setText("Seçilen W için tolerans tanımı bulunamadı.")
            return

        # Orijinal hesap çekirdeği
        YUVDER_MAX = (D1_max - D2_min) / 2.0
        YUVDER_MIN = (D1_min - D2_max) / 2.0

        CONKES_MAX = W + tol
        CONKES_MIN = W - tol

        # Germe düzeltmesi (orijinal: sqrt(DI/D2))
        if D2_min <= 0 or D2_max <= 0 or DI <= 0:
            self.lbl_err.setText("DI, D2_min ve D2_max pozitif olmalıdır.")
            return

        YUVICCONKES_MAX = CONKES_MAX * math.sqrt(DI / D2_min)
        YUVICCONKES_MIN = CONKES_MIN * math.sqrt(DI / D2_max)

        # Squeeze (orijinal formül)
        if YUVICCONKES_MAX == 0 or YUVICCONKES_MIN == 0:
            self.lbl_err.setText("Etkin kesit sıfır olamaz.")
            return

        SIKISMA_MAX = ((YUVICCONKES_MAX - YUVDER_MIN) / YUVICCONKES_MAX) * 100.0
        SIKISMA_MIN = ((YUVICCONKES_MIN - YUVDER_MAX) / YUVICCONKES_MIN) * 100.0

        # Germe oranı (orijinal: DI/D2_min)
        GERILME_ORANI = (DI / D2_min)

        # Yazdır
        self.le_YuvDer_Max.setText(f"{YUVDER_MAX:.2f}")
        self.le_YuvDer_Min.setText(f"{YUVDER_MIN:.2f}")
        self.le_ConKes_Max.setText(f"{CONKES_MAX:.2f}")
        self.le_ConKes_Min.setText(f"{CONKES_MIN:.2f}")
        self.le_YuvicConKes_Max.setText(f"{YUVICCONKES_MAX:.2f}")
        self.le_YuvicConKes_Min.setText(f"{YUVICCONKES_MIN:.2f}")
        self.le_S_Max.setText(f"{SIKISMA_MAX:.1f}")
        self.le_S_Min.setText(f"{SIKISMA_MIN:.1f}")
        self.le_Ger.setText(f"{GERILME_ORANI:.2f}")

        ok_smax = (10.0 <= SIKISMA_MAX <= 30.0)
        ok_smin = (10.0 <= SIKISMA_MIN <= 30.0)
        ok_ger = (0.95 <= GERILME_ORANI <= 1.00)

        self._set_badge(self.badge_Smax, ok_smax)
        self._set_badge(self.badge_Smin, ok_smin)
        self._set_badge(self.badge_Ger, ok_ger)

        if not ok_ger:
            self.lbl_GerNot.setText("D2 ya da O-Halka iç çapını (DI) değiştirmeyi deneyin...")
