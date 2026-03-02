# src/routes.py
# Category -> list of (display_name, module_import_path, class_name)

CATEGORIES = {
    "Basınçlı Kap": [
        ("Gövde Et Kalınlığı", "modules.mbetkalinligi", "MbEtKalinligiModule"),
        ("Elips Kubbe", "modules.elipskubbe", "ElipsKubbeModule"),
    ],
    "Cıvatalar / Diş": [
        ("Cıvata Sayısı (Eksenel)", "modules.civatasayisi", "CivataSayisiModule"),
        ("Metrik Diş", "modules.metrikdis", "MetrikDisModule"),
        ("Radyal Cıvata Kesme", "modules.radyalcivatasayisi", "RadyalCivataSayisiModule"),
    ],
    "Sızdırmazlık (O-Ring)": [
        ("Alın Conta", "modules.alinconta", "AlinContaModule"),
        ("Çap Conta", "modules.capconta", "CapContaModule"),
        ("Alın Conta Civata Yerleşimi", "modules.alincontacivata", "AlinContaCivataModule"),
    ],
    "Segman": [
        ("Segman Dayanım", "modules.segmandayanim", "SegmanDayanimModule"),
    ],
}
