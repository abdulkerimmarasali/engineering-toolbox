# src/modules/segman_dayanim.py
# Revision Notes (2026-03-02)
# - QDialog + loadUi kaldırıldı; tek dosyada QWidget tabanlı modül olarak yeniden yazıldı.
# - Geçersiz import (dec) ve mysql importları kaldırıldı. :contentReference[oaicite:0]{index=0}
# - Navigasyon index bağımlı değil: go_back callback ile "← Geri".
# - Etiket standardı: anlam merkezli + birimler görünür, sembol parantez içinde.
# - Hesap çekirdeği korunmuştur:
#     Alan = π*D^2/4
#     F = MEOP*S*Alan
#     A_kesme = π*D_kesme*t
#     τ = F/A_kesme
#     FS = τ_izin/τ
#     kriter: FS ≥ 1.5

import math
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QFormLayout
)
from PyQt5.QtCore import Qt

from src.utils import parse_float


class SegmanDayanimModule(QWidget):
    """
    Segman dayanım kontrolü (kesme) hesabı.

    Girdiler:
      - Çalışma basıncı (MEOP) [bar]*
      - Emniyet katsayısı (S) [–]
      - Basınç etki çapı / iç çap (D) [mm]
      - Kesme çapı (D_kesme) [mm]
      - Segman kalınlığı (t) [mm]
      - İzin verilebilir kesme gerilmesi (τ_izin) [MPa veya birim?]*

    Çıktılar:
      - Eksenel kuvvet (F) [N?]
      - Kesme alanı (A_kesme) [mm²]
      - Kesme gerilmesi (τ) [birim?]
      - Emniyet katsayısı (FS) [–]  (FS = τ_izin/τ)
      - Uygunluk: FS ≥ 1.5

    Not:
      Orijinal modülde basınç/kuvvet birim dönüşümü yapılmadığı için çıktılar giriş birimleriyle tutarlıdır.
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
        title = QLabel("Segman Dayanım (Kesme) Kontrolü")
        title.setStyleSheet("font-weight:700; font-size:16px;")
        header.addWidget(btn_back, 0, Qt.AlignLeft)
        header.addWidget(title, 1, Qt.AlignLeft)
        header.addStretch(1)
        root.addLayout(header)

        # Inputs card
        gb_in = QGroupBox("Girdiler")
        form_in = QFormLayout(gb_in)
        form_in.setHorizontalSpacing(14)
        form_in.setVerticalSpacing(10)

        self.le_MEOP = QLineEdit(); self.le_MEOP.setPlaceholderText("Örn: 10")
        self.le_S = QLineEdit(); self.le_S.setPlaceholderText("Örn: 1.5")
        self.le_D = QLineEdit(); self.le_D.setPlaceholderText("Örn: 120")
        self.le_D_kesme = QLineEdit(); self.le_D_kesme.setPlaceholderText("Örn: 80")
        self.le_t = QLineEdit(); self.le_t.setPlaceholderText("Örn: 3.0")
        self.le_tau_izin = QLineEdit(); self.le_tau_izin.setPlaceholderText("Örn: 150")

        form_in.addRow("Çalışma basıncı (MEOP) [bar]*", self.le_MEOP)
        form_in.addRow("Emniyet katsayısı (S) [–]", self.le_S)
        form_in.addRow("Basınç etki çapı / iç çap (D) [mm]", self.le_D)
        form_in.addRow("Kesme çapı (D_kesme) [mm]", self.le_D_kesme)
        form_in.addRow("Segman kalınlığı (t) [mm]", self.le_t)
        form_in.addRow("İzin verilebilir kesme gerilmesi (τ_izin) [–]*", self.le_tau_izin)

        note = QLabel("*Not: Orijinal kodda birim dönüşümü yoktur; sonuçlar girişlerle tutarlıdır.")
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

        # Outputs card
        gb_out = QGroupBox("Sonuçlar")
        form_out = QFormLayout(gb_out)
        form_out.setHorizontalSpacing(14)
        form_out.setVerticalSpacing(10)

        self.le_F = QLineEdit(); self.le_F.setReadOnly(True)
        self.le_A_kesme = QLineEdit(); self.le_A_kesme.setReadOnly(True)
        self.le_tau = QLineEdit(); self.le_tau.setReadOnly(True)
        self.le_FS = QLineEdit(); self.le_FS.setReadOnly(True)

        self.badge_FS = QLabel("")
        self._set_badge(self.badge_FS, None)

        row_fs = QHBoxLayout()
        row_fs.addWidget(self.le_FS, 1)
        row_fs.addWidget(self.badge_FS, 0)

        form_out.addRow("Eksenel kuvvet (F) [–]", self.le_F)
        form_out.addRow("Kesme alanı (A_kesme) [mm²]", self.le_A_kesme)
        form_out.addRow("Kesme gerilmesi (τ) [–]", self.le_tau)
        form_out.addRow("Emniyet katsayısı (FS) [–]", row_fs)

        root.addWidget(gb_out)

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

    # ---------------- Logic ----------------
    def calculate(self):
        self.lbl_err.setText("")
        self._set_badge(self.badge_FS, None)

        required = [
            (self.le_MEOP, "MEOP"),
            (self.le_S, "S"),
            (self.le_D, "D"),
            (self.le_D_kesme, "D_kesme"),
            (self.le_t, "t"),
            (self.le_tau_izin, "τ_izin"),
        ]
        for le, _name in required:
            if not le.text().strip():
                self.lbl_err.setText("Lütfen tüm değerleri giriniz.")
                return

        try:
            MEOP = parse_float(self.le_MEOP.text().strip(), "Çalışma basıncı (MEOP)")
            S = parse_float(self.le_S.text().strip(), "Emniyet katsayısı (S)")
            D = parse_float(self.le_D.text().strip(), "Çap (D)")
            D_kesme = parse_float(self.le_D_kesme.text().strip(), "Kesme çapı (D_kesme)")
            t = parse_float(self.le_t.text().strip(), "Kalınlık (t)")
            tau_izin = parse_float(self.le_tau_izin.text().strip(), "İzin verilebilir kesme gerilmesi (τ_izin)")
        except Exception as e:
            self.lbl_err.setText(str(e))
            return

        if D <= 0 or D_kesme <= 0 or t <= 0:
            self.lbl_err.setText("D, D_kesme ve t pozitif olmalıdır.")
            return

        # Orijinal çekirdek
        Alan = math.pi * (D * D) / 4.0
        F = MEOP * S * Alan

        A_kesme = math.pi * D_kesme * t
        if A_kesme <= 0:
            self.lbl_err.setText("Kesme alanı pozitif olmalıdır.")
            return

        tau = F / A_kesme
        if tau == 0:
            self.lbl_err.setText("Kesme gerilmesi sıfır çıktı; girdileri kontrol edin.")
            return

        FS = tau_izin / tau

        # Yazdır
        self.le_F.setText(f"{F:.1f}")
        self.le_A_kesme.setText(f"{A_kesme:.1f}")
        self.le_tau.setText(f"{tau:.1f}")
        self.le_FS.setText(f"{FS:.2f}")

        ok = (FS >= 1.5)
        self._set_badge(self.badge_FS, ok)
