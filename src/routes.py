# src/routes.py
CATEGORIES = {
    "Basınçlı Kap": [
        ("Gövde Et Kalınlığı", "modules.mbetkalinligi", "MbEtKalinligiModule"),
        ("Elips Kubbe", "modules.elipskubbe", "ElipsKubbeModule"),
    ],
    "Cıvatalar / Diş": [
        ("Cıvata Sayısı (Eksenel)", "modules.civatasayisi", "CivataSayisiModule"),
        ("Metrik Diş", "modules.metrikdis", "MetrikDisModule"),
        ("Radyal Cıvata Kesme", "modules.radyalcivata", "RadyalCivataModule"),
    ],
    "Sızdırmazlık (O-Ring)": [
        ("Alın Conta", "modules.alinconta", "AlinContaModule"),
        ("Çap Conta", "modules.capconta", "CapContaModule"),
        ("Alın Conta Civata Yerleşimi", "modules.alincontacivata", "AlinContaCivataModule"),
    ],
    "Segman": [
        ("Segman Dayanım", "modules.segman", "SegmanModule"),
    ],
}
