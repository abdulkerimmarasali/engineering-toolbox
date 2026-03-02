# src/modules/alin_conta.py
# Revision Notes (2026-02-26)
# - UI dosyası (loadUi) kaldırıldı; tek dosyada QWidget tabanlı modül olarak yeniden yazıldı.
# - Geçersiz import (dec) ve mysql/sqlite3 doğrudan bağlantıları kaldırıldı; DB erişimi db.py üzerinden yapılır.
# - Navigasyon index bağımlı değil: go_back callback ile "← Geri".
# - Etiket standardı: anlam merkezli + birim görünür, sembol parantez içinde.
# - Hesap çekirdeği (ID/OD, DE, Smax/Smin ve uygunluk 10–30%) korunmuştur.
# Kaynak: orijinal modül :contentReference[oaicite:0]{index=0}

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox,
    QFormLayout, QComboBox, QLineEdit, QMessageBox
)
from PyQt5.QtCore import Qt

from db import fetch_all
from utils import parse_float


class AlinContaModule(QWidget):
    """
    Alın Conta (O-Ring) modülü.
    - W seçimine göre DI listesi DB'den gelir.
    - DE = DI + 2W
    - ID/OD üretim hedefleri (X tabanlı) ve toleranslı sıkışma: Smax/Smin
    - Uygunluk bandı: 10–30 %
    """

    def __init__(self, go_back_callback):
        super().__init__()
        self.go_back = go_back_callback

        # W -> (DI tablo adı, W_tol, X, T, T_tol)
        # (Mevcut koddaki sabitler korunmuştur.)
        self._W_RULES = {
            1.78: ("oring_w_178", 0.08, 2.3, 1.3, 0.05),
            2.62: ("oring_w_262", 0.08, 3.4, 2.0, 0.05),
            3.53: ("oring_w_353", 0.10, 4.5, 2.75, 0.05),
            5.33: ("oring_w_533", 0.13, 6.9, 4.3, 0.05),
            6.99: ("oring_w_699", 0.15, 8.4, 5.8, 0.05),
        }

        self._build_ui()
        self._load_W_options()

    # ---------------- UI ----------------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        # Header
        header = QHBoxLayout()
        self.btn_back = QPushButton("← Geri")
        self.btn_back.clicked.connect(self.go_back)
        self.lbl_title = QLabel("Alın Conta Hesabı (O-Ring)")
        self.lbl_title.setStyleSheet("font-weight:700; font-size:16px;")
        header.addWidget(self.btn_back, 0, Qt.AlignLeft)
        header.addWidget(self.lbl_title, 1, Qt.AlignLeft)
        header.addStretch(1)
        root.addLayout(header)

        # Inputs card
        gb_in = QGroupBox("Girdiler")
        form_in = QFormLayout(gb_in)
        form_in.setLabelAlignment(Qt.AlignLeft)
        form_in.setFormAlignment(Qt.AlignTop)
        form_in.setHorizontalSpacing(14)
        form_in.setVerticalSpacing(10)

        self.cb_W = QComboBox()
        self.cb_DI = QComboBox()
        self.cb_DI.setEnabled(False)

        self.le_DE = QLineEdit()
        self.le_DE.setReadOnly(True)

        self.le_d = QLineEdit()  # gap
        self.le_d.setPlaceholderText("Örn: 0.20")

        # Manuel kanal derinliği (opsiyonel)
        self.le_ManT = QLineEdit()
        self.le_ManT.setPlaceholderText("Boş bırakılırsa otomatik T kullanılır")
        self.le_ManT_tol = QLineEdit()
        self.le_ManT_tol.setPlaceholderText("Boş bırakılırsa otomatik tolerans kullanılır")

        form_in.addRow("O-ring kesit çapı (W) [mm]", self.cb_W)
        form_in.addRow("O-ring iç çapı (DI) [mm]", self.cb_DI)
        form_in.addRow("Hesaplanan dış çap (DE = DI + 2W) [mm]", self.le_DE)
        form_in.addRow("İlave açıklık / gap (d) [mm]", self.le_d)
        form_in.addRow("Kanal derinliği (T) [mm] (manuel)", self.le_ManT)
        form_in.addRow("Kanal derinliği toleransı (T_tol) [mm] (manuel)", self.le_ManT_tol)

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

        # Results card
        gb_out = QGroupBox("Sonuçlar")
        form_out = QFormLayout(gb_out)
        form_out.setHorizontalSpacing(14)
        form_out.setVerticalSpacing(10)

        self.le_ID = QLineEdit(); self.le_ID.setReadOnly(True)
        self.le_OD = QLineEdit(); self.le_OD.setReadOnly(True)

        self.le_ID_tol = QLineEdit(); self.le_ID_tol.setReadOnly(True)
        self.le_OD_tol = QLineEdit(); self.le_OD_tol.setReadOnly(True)

        self.le_T = QLineEdit(); self.le_T.setReadOnly(True)
        self.le_T_tol = QLineEdit(); self.le_T_tol.setReadOnly(True)

        self.le_R1R2 = QLineEdit(); self.le_R1R2.setReadOnly(True)
        self.le_R1R2_tol = QLineEdit(); self.le_R1R2_tol.setReadOnly(True)

        self.le_Smax = QLineEdit(); self.le_Smax.setReadOnly(True)
        self.le_Smin = QLineEdit(); self.le_Smin.setReadOnly(True)

        self.badge_Smax = QLabel("")
        self.badge_Smin = QLabel("")
        self._set_badge(self.badge_Smax, None)
        self._set_badge(self.badge_Smin, None)

        row_smax = QHBoxLayout()
        row_smax.addWidget(self.le_Smax, 1)
        row_smax.addWidget(self.badge_Smax, 0)

        row_smin = QHBoxLayout()
        row_smin.addWidget(self.le_Smin, 1)
        row_smin.addWidget(self.badge_Smin, 0)

        form_out.addRow("Hedef iç çap (ID) [mm]", self.le_ID)
        form_out.addRow("Hedef dış çap (OD) [mm]", self.le_OD)
        form_out.addRow("ID toleransı (ID_tol) [mm]", self.le_ID_tol)
        form_out.addRow("OD toleransı (OD_tol) [mm]", self.le_OD_tol)
        form_out.addRow("Kanal derinliği (T) [mm]", self.le_T)
        form_out.addRow("Kanal derinliği toleransı (T_tol) [mm]", self.le_T_tol)
        form_out.addRow("Köşe yarıçapı (R1=R2) [mm]", self.le_R1R2)
        form_out.addRow("Köşe yarıçapı toleransı (R_tol) [mm]", self.le_R1R2_tol)
        form_out.addRow("Hesaplanan sıkışma (S_max) [%]", row_smax)
        form_out.addRow("Hesaplanan sıkışma (S_min) [%]", row_smin)

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
            lbl.setStyleSheet("background-color: #E0E0E0; color: #303030; border-radius:6px; font-weight:700;")
        elif ok:
            lbl.setText("UYGUN")
            lbl.setStyleSheet("background-color: #2E7D32; color: white; border-radius:6px; font-weight:700;")
        else:
            lbl.setText("UYGUN DEĞİL")
            lbl.setStyleSheet("background-color: #C62828; color: white; border-radius:6px; font-weight:700;")

    # ---------------- DB Loading ----------------
    def _load_W_options(self):
        self.cb_W.blockSignals(True)
        self.cb_W.clear()

        rows = fetch_all("SELECT W FROM oring_W_tol")
        W_list = []
        for r in rows:
            try:
                W_list.append(float(r[0]))
            except Exception:
                continue

        # DB'den gelmezse fallback: rule set
        if not W_list:
            W_list = sorted(self._W_RULES.keys())

        for w in sorted(set(W_list)):
            self.cb_W.addItem(f"{w:.2f}", w)

        self.cb_W.blockSignals(False)

        # İlk yükleme
        if self.cb_W.count() > 0:
            self._on_W_changed(self.cb_W.currentText())

    def _load_DI_options(self, W: float):
        self.cb_DI.blockSignals(True)
        self.cb_DI.clear()

        table = self._W_RULES.get(W, (None, 0, 0, 0, 0))[0]
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

        # DI değişimi ile DE otomatik
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

        W = self.cb_W.currentData()
        DI = self.cb_DI.currentData()

        if W is None:
            self.lbl_err.setText("Kesit çapı (W) seçiniz.")
            return
        if DI is None:
            self.lbl_err.setText("İç çap (DI) seçiniz.")
            return

        # d zorunlu (orijinal davranış)
        if not self.le_d.text().strip():
            self.lbl_err.setText("İlave açıklık / gap (d) giriniz.")
            return

        try:
            d = parse_float(self.le_d.text().strip(), "İlave açıklık / gap (d)")
        except Exception as e:
            self.lbl_err.setText(str(e))
            return

        W = float(W)
        DI = float(DI)
        DE = DI + 2.0 * W
        self.le_DE.setText(f"{DE:.3f}")

        # Kural seti (orijinal sabitler)
        table, W_tol, X, T, T_tol = self._W_RULES.get(W, (None, 0.0, 0.0, 0.0, 0.0))

        # Manuel T override (ikisi doluysa)
        manT = self.le_ManT.text().strip()
        manTtol = self.le_ManT_tol.text().strip()
        if manT and manTtol:
            try:
                T = parse_float(manT, "Kanal derinliği (T)")
                T_tol = parse_float(manTtol, "Kanal derinliği toleransı (T_tol)")
            except Exception as e:
                self.lbl_err.setText(str(e))
                return
        elif manT or manTtol:
            self.lbl_err.setText("Manuel giriş için T ve T_tol birlikte girilmelidir.")
            return

        # Sabit toleranslar (orijinal modüle uyumlu)
        ID_tol = 0.1
        OD_tol = 0.1
        R1R2 = 0.3
        R1R2_tol = 0.1

        # ID/OD hedefleri (orijinal)
        ID = W + DI - X
        OD = W + DI + X

        # Sıkışma hesapları (orijinal formül korunmuştur)
        # Smax: (W_max - T_min - d) / W_max
        S_max = (((W + W_tol) - (T - T_tol)) - d) / (W + W_tol) * 100.0
        # Smin: (W_min - T_max - d) / W_min
        S_min = (((W - W_tol) - (T + T_tol)) - d) / (W - W_tol) * 100.0

        # UI yazdır
        self.le_ID.setText(f"{ID:.3f}")
        self.le_OD.setText(f"{OD:.3f}")
        self.le_ID_tol.setText(f"{ID_tol:.3f}")
        self.le_OD_tol.setText(f"{OD_tol:.3f}")
        self.le_T.setText(f"{T:.3f}")
        self.le_T_tol.setText(f"{T_tol:.3f}")
        self.le_R1R2.setText(f"{R1R2:.3f}")
        self.le_R1R2_tol.setText(f"{R1R2_tol:.3f}")

        self.le_Smax.setText(f"{S_max:.1f}")
        self.le_Smin.setText(f"{S_min:.1f}")

        ok_smax = (10.0 <= S_max <= 30.0)
        ok_smin = (10.0 <= S_min <= 30.0)

        self._set_badge(self.badge_Smax, ok_smax)
        self._set_badge(self.badge_Smin, ok_smin)
