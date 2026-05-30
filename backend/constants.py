"""
CROSSROAD — Seed data and constants.
This is the master list that bootstraps the bulk crawler.
All entries are publicly known officials from public records.
"""

PARTY_COLORS = {
    "PDIP":       "#e63946",
    "Gerindra":   "#1d3557",
    "Golkar":     "#f0b429",
    "PKB":        "#22c55e",
    "Demokrat":   "#3b82f6",
    "PKS":        "#0f4c3a",
    "Nasdem":     "#f97316",
    "PAN":        "#a855f7",
    "PPP":        "#059669",
    "PSI":        "#ec4899",
    "Hanura":     "#78716c",
    "Perindo":    "#0ea5e9",
    "Independen": "#6b7280",
    "Gerindra/Koalisi": "#1d3557",
}

KNOWN_PARTIES = list(PARTY_COLORS.keys())

# ── Master seed list of Indonesian officials ──────────────────────────────────
# Format: {name, role_type, position, party, faction, province/region, dapil}
SEED_OFFICIALS = [
    # ── PRESIDEN / WAPRES ────────────────────────────────────────────────────
    {"name": "Prabowo Subianto",        "role_type": "presiden",  "position": "Presiden RI ke-8",                      "party": "Gerindra",   "faction": "Gerindra",  "province": "Nasional"},
    {"name": "Gibran Rakabuming Raka",  "role_type": "wapres",    "position": "Wakil Presiden RI ke-14",               "party": "Independen", "faction": None,        "province": "Nasional"},

    # ── KABINET MERAH PUTIH 2024-2029 ────────────────────────────────────────
    {"name": "Sri Mulyani Indrawati",   "role_type": "menteri",   "position": "Menteri Keuangan",                      "party": "Independen", "province": "Jakarta"},
    {"name": "Sugiono",                 "role_type": "menteri",   "position": "Menteri Luar Negeri",                   "party": "Gerindra",   "province": "Jakarta"},
    {"name": "Agus Harimurti Yudhoyono","role_type": "menteri",   "position": "Menteri Koordinator Bidang Infrastruktur","party": "Demokrat",  "province": "Jakarta"},
    {"name": "Erick Thohir",            "role_type": "menteri",   "position": "Menteri BUMN",                          "party": "Independen", "province": "Jakarta"},
    {"name": "Budi Gunawan",            "role_type": "menteri",   "position": "Menko Polhukam",                        "party": "Independen", "province": "Jakarta"},
    {"name": "Airlangga Hartarto",      "role_type": "menteri",   "position": "Mantan Menko Perekonomian / Ketua Golkar","party": "Golkar",   "province": "Jakarta"},
    {"name": "Zulkifli Hasan",          "role_type": "menteri",   "position": "Menteri Perdagangan",                   "party": "PAN",        "province": "Jakarta"},
    {"name": "Agus Gumiwang Kartasasmita","role_type":"menteri",  "position": "Menko Perekonomian",                    "party": "Golkar",     "province": "Jakarta"},
    {"name": "Saifullah Yusuf",         "role_type": "menteri",   "position": "Menteri Sosial",                        "party": "PKB",        "province": "Jakarta"},
    {"name": "Budi Arie Setiadi",       "role_type": "menteri",   "position": "Menteri Komunikasi",                    "party": "PDIP",       "province": "Jakarta"},
    {"name": "Basuki Hadimuljono",      "role_type": "menteri",   "position": "Menteri PUPR",                          "party": "Independen", "province": "Jakarta"},
    {"name": "Natalius Pigai",          "role_type": "menteri",   "position": "Menteri HAM",                           "party": "Independen", "province": "Jakarta"},
    {"name": "Meutya Hafid",            "role_type": "menteri",   "position": "Menteri Kominfo",                       "party": "Golkar",     "province": "Jakarta"},
    {"name": "Retno Marsudi",           "role_type": "menteri",   "position": "Penasihat Khusus Presiden",             "party": "Independen", "province": "Jakarta"},
    {"name": "Abdul Mu'ti",             "role_type": "menteri",   "position": "Menteri Pendidikan Dasar",              "party": "Independen", "province": "Jakarta"},
    {"name": "Hasan Nasbi",             "role_type": "menteri",   "position": "Kepala PCO",                            "party": "Independen", "province": "Jakarta"},

    # ── DPR RI 2024-2029 — PIMPINAN & KOMISI ─────────────────────────────────
    {"name": "Puan Maharani",           "role_type": "dpr",       "position": "Ketua DPR RI",                          "party": "PDIP",       "faction": "PDIP",      "dapil": "Jawa Tengah V",     "province": "Jawa Tengah"},
    {"name": "Sufmi Dasco Ahmad",       "role_type": "dpr",       "position": "Wakil Ketua DPR RI",                    "party": "Gerindra",   "faction": "Gerindra",  "dapil": "Banten III",        "province": "Banten"},
    {"name": "Adies Kadir",             "role_type": "dpr",       "position": "Wakil Ketua DPR RI",                    "party": "Golkar",     "faction": "Golkar",    "dapil": "Jawa Timur I",      "province": "Jawa Timur"},
    {"name": "Saan Mustopa",            "role_type": "dpr",       "position": "Wakil Ketua DPR RI",                    "party": "Nasdem",     "faction": "Nasdem",    "dapil": "Jawa Barat VII",    "province": "Jawa Barat"},
    {"name": "Cucun Ahmad Syamsurijal", "role_type": "dpr",       "position": "Wakil Ketua DPR RI",                    "party": "PKB",        "faction": "PKB",       "dapil": "Jawa Barat II",     "province": "Jawa Barat"},
    {"name": "Ahmad Muzani",            "role_type": "dpr",       "position": "Ketua MPR RI",                          "party": "Gerindra",   "faction": "Gerindra",  "dapil": "Lampung I",         "province": "Lampung"},
    {"name": "Muhaimin Iskandar",       "role_type": "dpr",       "position": "Wakil Ketua MPR RI / Ketua PKB",        "party": "PKB",        "faction": "PKB",       "dapil": "Jawa Timur IX",     "province": "Jawa Timur"},
    {"name": "Zulkifli Hasan",          "role_type": "dpr",       "position": "Ketua MPR RI / Ketua PAN",              "party": "PAN",        "faction": "PAN",       "dapil": "Lampung II",        "province": "Lampung"},
    {"name": "Bambang Wuryanto",        "role_type": "dpr",       "position": "Anggota DPR RI / Ketua Komisi III",     "party": "PDIP",       "faction": "PDIP",      "dapil": "Jawa Tengah VIII",  "province": "Jawa Tengah"},
    {"name": "Utut Adianto",            "role_type": "dpr",       "position": "Anggota DPR RI",                        "party": "PDIP",       "faction": "PDIP",      "dapil": "Jawa Tengah VI",    "province": "Jawa Tengah"},
    {"name": "Akbar Faizal",            "role_type": "dpr",       "position": "Anggota DPR RI",                        "party": "Nasdem",     "faction": "Nasdem",    "dapil": "Sulawesi Selatan II","province": "Sulawesi Selatan"},
    {"name": "Ahmad Syaikhu",           "role_type": "dpr",       "position": "Presiden PKS / Anggota DPR RI",         "party": "PKS",        "faction": "PKS",       "dapil": "Jawa Barat VI",     "province": "Jawa Barat"},
    {"name": "Dasco Ahmad",             "role_type": "dpr",       "position": "Wakil Ketua DPR RI",                    "party": "Gerindra",   "faction": "Gerindra",  "dapil": "Banten III",        "province": "Banten"},
    {"name": "Habiburokhman",           "role_type": "dpr",       "position": "Ketua Komisi III DPR RI",               "party": "Gerindra",   "faction": "Gerindra",  "dapil": "Lampung II",        "province": "Lampung"},
    {"name": "Fadli Zon",               "role_type": "menteri",   "position": "Menteri Kebudayaan",                    "party": "Gerindra",   "province": "Jakarta"},
    {"name": "Desmond J. Mahesa",       "role_type": "dpr",       "position": "Anggota DPR RI",                        "party": "Gerindra",   "faction": "Gerindra",  "dapil": "Banten II",         "province": "Banten"},
    {"name": "Effendi Simbolon",        "role_type": "dpr",       "position": "Anggota DPR RI",                        "party": "PDIP",       "faction": "PDIP",      "dapil": "Sumatera Utara III","province": "Sumatera Utara"},
    {"name": "Masinton Pasaribu",       "role_type": "dpr",       "position": "Anggota DPR RI",                        "party": "PDIP",       "faction": "PDIP",      "dapil": "Sumatera Utara II", "province": "Sumatera Utara"},
    {"name": "Rieke Diah Pitaloka",     "role_type": "dpr",       "position": "Anggota DPR RI / Ketua Komisi IX",      "party": "PDIP",       "faction": "PDIP",      "dapil": "Jawa Barat VII",    "province": "Jawa Barat"},
    {"name": "Charles Honoris",         "role_type": "dpr",       "position": "Anggota DPR RI",                        "party": "PDIP",       "faction": "PDIP",      "dapil": "DKI Jakarta I",     "province": "DKI Jakarta"},

    # ── GUBERNUR ─────────────────────────────────────────────────────────────
    {"name": "Ridwan Kamil",            "role_type": "gubernur",  "position": "Gubernur DKI Jakarta terpilih",         "party": "Golkar",     "province": "DKI Jakarta"},
    {"name": "Pramono Anung",           "role_type": "gubernur",  "position": "Gubernur DKI Jakarta terpilih (PDIP)",  "party": "PDIP",       "province": "DKI Jakarta"},
    {"name": "Khofifah Indar Parawansa","role_type": "gubernur",  "position": "Gubernur Jawa Timur",                   "party": "PKB",        "province": "Jawa Timur"},
    {"name": "Dedi Mulyadi",            "role_type": "gubernur",  "position": "Gubernur Jawa Barat terpilih",          "party": "Golkar",     "province": "Jawa Barat"},
    {"name": "Ganjar Pranowo",          "role_type": "gubernur",  "position": "Mantan Gubernur Jawa Tengah",           "party": "PDIP",       "province": "Jawa Tengah"},
    {"name": "Anies Baswedan",          "role_type": "gubernur",  "position": "Mantan Gubernur DKI Jakarta",           "party": "Independen", "province": "DKI Jakarta"},
    {"name": "Andi Sudirman Sulaiman",  "role_type": "gubernur",  "position": "Gubernur Sulawesi Selatan",             "party": "Gerindra",   "province": "Sulawesi Selatan"},
    {"name": "Al Haris",                "role_type": "gubernur",  "position": "Gubernur Jambi",                        "party": "Demokrat",   "province": "Jambi"},
    {"name": "Rohidin Mersyah",         "role_type": "gubernur",  "position": "Gubernur Bengkulu",                     "party": "Golkar",     "province": "Bengkulu"},
    {"name": "Isran Noor",              "role_type": "gubernur",  "position": "Mantan Gubernur Kalimantan Timur",      "party": "Nasdem",     "province": "Kalimantan Timur"},
    {"name": "Syamsuar",                "role_type": "gubernur",  "position": "Mantan Gubernur Riau",                  "party": "Golkar",     "province": "Riau"},
    {"name": "Edy Rahmayadi",           "role_type": "gubernur",  "position": "Mantan Gubernur Sumatera Utara",        "party": "Gerindra",   "province": "Sumatera Utara"},
    {"name": "Nova Iriansyah",          "role_type": "gubernur",  "position": "Mantan Gubernur Aceh",                  "party": "Demokrat",   "province": "Aceh"},
    {"name": "Muhammad Ridho Ficardo",  "role_type": "gubernur",  "position": "Mantan Gubernur Lampung",               "party": "Demokrat",   "province": "Lampung"},

    # ── BUPATI / WALIKOTA ─────────────────────────────────────────────────────
    {"name": "Bobby Nasution",          "role_type": "bupati",    "position": "Mantan Wali Kota Medan / Gubernur Sumut terpilih","party": "Gerindra","province": "Sumatera Utara"},
    {"name": "Gibran Rakabuming Raka",  "role_type": "bupati",    "position": "Mantan Wali Kota Solo",                 "party": "PDIP",       "province": "Jawa Tengah"},
    {"name": "Danny Pomanto",           "role_type": "bupati",    "position": "Wali Kota Makassar",                    "party": "Independen", "province": "Sulawesi Selatan"},
    {"name": "Eri Cahyadi",             "role_type": "bupati",    "position": "Wali Kota Surabaya terpilih",           "party": "PDIP",       "province": "Jawa Timur"},
    {"name": "Bima Arya",               "role_type": "bupati",    "position": "Mantan Wali Kota Bogor",                "party": "PAN",        "province": "Jawa Barat"},
    {"name": "Muhammad Rudi",           "role_type": "bupati",    "position": "Wali Kota Batam",                       "party": "PKS",        "province": "Kepulauan Riau"},
    {"name": "Adnan Purichta Ichsan",   "role_type": "bupati",    "position": "Bupati Gowa",                           "party": "Nasdem",     "province": "Sulawesi Selatan"},
    {"name": "Rusma Yul Anwar",         "role_type": "bupati",    "position": "Bupati Pesisir Selatan",                "party": "Golkar",     "province": "Sumatera Barat"},

    # ── DPRD (Ketua-ketua Provinsi) ───────────────────────────────────────────
    {"name": "Fuad Bernadi",            "role_type": "dprd",      "position": "Ketua DPRD Jawa Barat",                 "party": "Gerindra",   "faction": "Gerindra",  "province": "Jawa Barat"},
    {"name": "Khoirul Anam",            "role_type": "dprd",      "position": "Ketua DPRD Jawa Tengah",                "party": "PKB",        "faction": "PKB",       "province": "Jawa Tengah"},
    {"name": "Adde Rosi Khairunnisa",   "role_type": "dprd",      "position": "Wakil Ketua DPRD Banten",               "party": "Golkar",     "faction": "Golkar",    "province": "Banten"},
    {"name": "Mabes Harahap",           "role_type": "dprd",      "position": "Ketua DPRD Sumatera Utara",             "party": "Demokrat",   "faction": "Demokrat",  "province": "Sumatera Utara"},
    {"name": "Asikin Fikri",            "role_type": "dprd",      "position": "Ketua DPRD Sulawesi Selatan",           "party": "Golkar",     "faction": "Golkar",    "province": "Sulawesi Selatan"},
    {"name": "M. Iqbal Suhaili",        "role_type": "dprd",      "position": "Ketua DPRD NTB",                        "party": "PKB",        "faction": "PKB",       "province": "Nusa Tenggara Barat"},

    # ── Historical / prominent figures ────────────────────────────────────────
    {"name": "Megawati Soekarnoputri",  "role_type": "dpr",       "position": "Ketua Umum PDIP",                       "party": "PDIP",       "faction": "PDIP",      "province": "Nasional"},
    {"name": "Susilo Bambang Yudhoyono","role_type": "presiden",  "position": "Presiden RI ke-6 / Ketua Dewan Pembina Demokrat","party":"Demokrat","province": "Nasional"},
    {"name": "Joko Widodo",             "role_type": "presiden",  "position": "Presiden RI ke-7",                      "party": "PDIP",       "province": "Nasional"},
]

# ── Official government data sources ─────────────────────────────────────────
OFFICIAL_SOURCES = {
    "dpr":      "https://www.dpr.go.id/anggota",
    "dprd":     "https://dprd.go.id",
    "menteri":  "https://www.setneg.go.id/baca/index/kabinet_merah_putih",
    "gubernur": "https://kemendagri.go.id",
    "bupati":   "https://kemendagri.go.id",
    "wiki_list_dpr":      "https://id.wikipedia.org/wiki/Daftar_anggota_Dewan_Perwakilan_Rakyat_2024%E2%80%932029",
    "wiki_kabinet":       "https://id.wikipedia.org/wiki/Kabinet_Merah_Putih",
    "wiki_gubernur":      "https://id.wikipedia.org/wiki/Daftar_gubernur_di_Indonesia",
}

# ── Indonesian news RSS / search endpoints ────────────────────────────────────
NEWS_SOURCES = [
    {"name": "Tempo",         "search": "https://www.tempo.co/search?q={q}",                    "base": "https://tempo.co"},
    {"name": "Kompas",        "search": "https://search.kompas.com/search/?q={q}",              "base": "https://kompas.com"},
    {"name": "Detik",         "search": "https://www.detik.com/search/searchall?query={q}&sortby=time", "base": "https://detik.com"},
    {"name": "CNN Indonesia", "search": "https://www.cnnindonesia.com/search?query={q}",        "base": "https://cnnindonesia.com"},
    {"name": "Antara",        "search": "https://www.antaranews.com/search?q={q}",              "base": "https://antaranews.com"},
    {"name": "Republika",     "search": "https://republika.co.id/search/{q}",                  "base": "https://republika.co.id"},
    {"name": "Tribun",        "search": "https://www.tribunnews.com/search?q={q}",              "base": "https://tribunnews.com"},
    {"name": "JPNN",          "search": "https://www.jpnn.com/search?keyword={q}",              "base": "https://jpnn.com"},
]

NEWS_CATEGORIES = {
    "corruption":  ["korupsi","suap","gratifikasi","kpk","tipikor","dakwaan","terdakwa","tersangka","pidana","bribery","fraud","kasus","ditangkap"],
    "election":    ["pemilu","pilkada","pileg","kampanye","calon","kandidat","kpu","pilpres","suara","menang","kalah","election","vote"],
    "family":      ["keluarga","istri","suami","anak","putra","putri","menikah","pernikahan","perceraian","family","spouse","children","wife"],
    "business":    ["bisnis","perusahaan","saham","usaha","investasi","proyek","kontrak","bumn","ceo","direktur","business","company","corporation","pabrik"],
    "policy":      ["kebijakan","peraturan","uu","undang","regulasi","program","anggaran","apbn","apbd","policy","regulation","budget","perpres","pp"],
    "legal":       ["hukum","sidang","pengadilan","hakim","jaksa","polisi","ditahan","vonis","tuntutan","penjara","kpk","tersangka","terdakwa"],
    "statement":   ["pernyataan","kritik","merespons","menyatakan","mengatakan","menanggapi","komentar","statement","says","claims"],
    "education":   ["pendidikan","sekolah","universitas","wisuda","akademik","beasiswa","kampus"],
    "military":    ["militer","tni","polri","pangdam","kapolri","jenderal","pamen","operasi","pertahanan"],
}
