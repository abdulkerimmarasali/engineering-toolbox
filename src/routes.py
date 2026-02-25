# src/routes.py
# Category -> list of (display_name, module_import_path, class_name)
CATEGORIES = {
    "Basınçlı Kap": [
        ("Gövde Et Kalınlığı", "src.modules.mbetkalinligi", "MbEtKalinligiModule"),
        ("Elips Kubbe", "src.modules.elipskubbe", "ElipsKubbeModule"),
    ],
    "Cıvatalar / Diş": [
        ("Cıvata Sayısı (Eksenel)", "src.modules.civatasayisi", "CivataSayisiModule"),
        ("Metrik Diş", "src.modules.metrikdis", "MetrikDisModule"),
        ("Radyal Cıvata Kesme", "src.modules.radyalcivata", "RadyalCivataModule"),
    ],
    "Sızdırmazlık (O-Ring)": [
        ("Alın Conta", "src.modules.alinconta", "AlinContaModule"),
        ("Çap Conta", "src.modules.capconta", "CapContaModule"),
        ("Alın Conta Civata Yerleşimi", "src.modules.alincontacivata", "AlinContaCivataModule"),
    ],
    "Segman": [
        ("Segman Dayanım", "src.modules.segman", "SegmanModule"),
    ],
}
