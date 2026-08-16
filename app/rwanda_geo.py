"""Administrative address data, scoped to this project's case-study district.

The system's case study is Bugesera District, so registration only needs to
capture Bugesera's own sectors, cells, and villages. Sourced from the Bugesera
entry of https://github.com/ngabovictor/Rwanda's data.json (a structured
District > Sector > Cell > Village dataset for the whole country): 15 sectors,
72 cells, 581 villages - matching NISR's published totals for the district
exactly. Cross-checked against an independent extraction from Rwanda Energy
Group's national village registry PDF; the two sources agreed on every sector,
cell, and village name (only cosmetic Roman-numeral-casing differences, e.g.
"Kagasa II" vs "Kagasa Ii" - this file uses the ngabovictor/Rwanda casing).
"""

BUGESERA_DISTRICT = "Bugesera"

# Simplified outer boundary of Bugesera District as [lat, lng] pairs (WGS84).
# Derived from geoBoundaries RWA ADM2 (NISR 2022 census mapping), reduced to
# ~90 vertices for a crisp polygon overlay without a heavy payload. Bounds:
# lat -2.438184..-2.028219, lng 29.959209..30.374481.
BUGESERA_BOUNDARY = [
    [-2.074183, 30.019346], [-2.085817, 30.017687], [-2.096636, 30.017091],
    [-2.107185, 30.017168], [-2.114777, 30.018831], [-2.120393, 30.012556],
    [-2.131285, 30.009745], [-2.141176, 29.999973], [-2.144743, 29.992689],
    [-2.14811, 29.98555], [-2.160227, 29.983308], [-2.167268, 29.983176],
    [-2.176199, 29.98256], [-2.187853, 29.985404], [-2.19965, 29.984684],
    [-2.206096, 29.988588], [-2.213424, 29.990216], [-2.222267, 29.988531],
    [-2.231991, 29.984023], [-2.243343, 29.984328], [-2.25208, 29.977968],
    [-2.263967, 29.973267], [-2.274371, 29.973461], [-2.285291, 29.967061],
    [-2.297926, 29.960633], [-2.311241, 29.964271], [-2.320438, 29.963764],
    [-2.330608, 29.966942], [-2.344457, 30.019516], [-2.3585, 30.043078],
    [-2.413449, 30.085725], [-2.438184, 30.135622], [-2.43026, 30.181058],
    [-2.402206, 30.198083], [-2.383111, 30.213359], [-2.368585, 30.227136],
    [-2.37169, 30.250871], [-2.375347, 30.287422], [-2.363688, 30.340127],
    [-2.358156, 30.363208], [-2.348352, 30.37242], [-2.346605, 30.363078],
    [-2.336981, 30.359021], [-2.329363, 30.358306], [-2.318169, 30.35596],
    [-2.307924, 30.345248], [-2.293802, 30.336212], [-2.28158, 30.328769],
    [-2.268711, 30.335864], [-2.246963, 30.337513], [-2.227284, 30.335195],
    [-2.207733, 30.321713], [-2.198755, 30.323504], [-2.203157, 30.311525],
    [-2.207056, 30.30418], [-2.204346, 30.295961], [-2.209186, 30.278797],
    [-2.195704, 30.275094], [-2.189409, 30.266729], [-2.176292, 30.264757],
    [-2.16519, 30.266775], [-2.151591, 30.273126], [-2.13866, 30.269465],
    [-2.13334, 30.267692], [-2.125181, 30.26819], [-2.113496, 30.269336],
    [-2.10555, 30.251666], [-2.097324, 30.247959], [-2.088301, 30.244819],
    [-2.073507, 30.244639], [-2.070737, 30.236148], [-2.069482, 30.221965],
    [-2.078458, 30.209303], [-2.066573, 30.201244], [-2.055316, 30.190853],
    [-2.038191, 30.185454], [-2.029624, 30.174187], [-2.031477, 30.162072],
    [-2.040781, 30.147577], [-2.042684, 30.135244], [-2.05166, 30.128739],
    [-2.058026, 30.119912], [-2.059231, 30.111793], [-2.05783, 30.101052],
    [-2.062665, 30.085918], [-2.068552, 30.077605], [-2.068281, 30.069071],
    [-2.065959, 30.055664], [-2.055362, 30.052391], [-2.058959, 30.038847],
    [-2.068908, 30.039353], [-2.069047, 30.025957], [-2.074183, 30.019346],
]

BUGESERA_SECTORS = {
    "Gashora": {
        "Biryogo": ["Bidudu", "Biryogo", "Buhoro", "Gihanama", "Kagarama", "Kanyonyomba", "Karutete", "Kivugiza", "Rugunga"],
        "Kabuye": ["Bidudu", "Kabuye", "Karizinge", "Rwagasiga", "Rweteto"],
        "Kagomasi": ["Akagako", "Kagomasi", "Kiruhura", "Kuruganda", "Runzenze", "Rushubi"],
        "Mwendo": ["Gaharwa", "Gisenyi", "Kayovu", "Ruhanga", "Ruhanura", "Rutanga"],
        "Ramiro": ["Dihiro", "Kagasa I", "Kagasa II", "Karusine I", "Karusine II", "Migina", "Munyinya", "Rweru I", "Rweru II"],
    },
    "Juru": {
        "Juru": ["Ayabakiza", "Bisagara", "Nyamigende", "Rugarama", "Rwamakara", "Twabagarama"],
        "Kabukuba": ["Gikana", "Gikurazo", "Kabukuba", "Kamatongo", "Majanja", "Mbuye", "Rushubi"],
        "Mugorore": ["Cyirabo", "Gatora", "Kajevuba", "Mugorore", "Murambi", "Rebero", "Rwamurama", "Tabarari"],
        "Musovu": ["Bitega", "Cyabasonga", "Cyingaju", "Kabeza", "Nyaruhuru"],
        "Rwinume": ["Gisororo", "Kabeza", "Katarara", "Kinihira", "Rwimpyisi", "Uwimpunga"],
    },
    "Kamabuye": {
        "Biharagu": ["Akanigo", "Biharagu", "Kanyonyera", "Munazi", "Muyigi", "Nyarurama", "Rubugu"],
        "Burenge": ["Akabazeyi", "Kagenge", "Murambo", "Nyabyondo", "Nyakariba", "Rebero", "Senga"],
        "Kampeka": ["Byimana", "Kampeka", "Mabuye", "Masangano", "Mbuganzeri", "Mparo", "Ndama", "Pamba I", "Pamba II"],
        "Nyakayaga": ["Akaje", "Fatinkanda", "Murago", "Murambi", "Ntungamo I", "Ntungamo II", "Nyakayaga"],
        "Tunda": ["Cyogamuyaga", "Mububa I", "Mububaya II", "Rubirizi", "Rusibya", "Tunda", "Twuruziramire", "Uwibiraro I", "Uwibiraro II", "Uwumusave"],
    },
    "Mareba": {
        "Bushenyi": ["Bigaga", "Bukumba", "Cyantwari", "Gasagara", "Gitega", "Kabeza", "Kagese", "Kagogo", "Kamasonga", "Mareba", "Muyange", "Rukoyoyo", "Runyonza", "Rususa"],
        "Gakomeye": ["Gatanga", "Gitwa", "Kabere", "Kajevuba", "Kamudeberi", "Kamunana", "Kanka", "Kaziranyenzi", "Rwintare"],
        "Nyamigina": ["Gafunzo", "Kabeza", "Kabingo", "Kabuye", "Karwana", "Ngugu", "Nyamigisha", "Ruhina", "Rusenyi", "Ruyenzi"],
        "Rango": ["Gatare", "Gatinza", "Gihoko", "Kabuga", "Kagarama", "Matinza", "Mbuga", "Rango", "Rusagara", "Rwabikwano"],
        "Rugarama": ["Gasagara", "Gatare", "Kayonza", "Keza", "Kururama", "Muyenzi", "Ruduha", "Rugarama", "Rutaka"],
    },
    "Mayange": {
        "Gakamba": ["Gacucu", "Gakamba", "Gisenyi", "Kamugenzi", "Karambo", "Kavumu", "Rukora"],
        "Kagenge": ["Biryogo", "Gakindo", "Gitaramuka", "Karama", "Kiruhura", "Remera", "Rukindo", "Taba", "Tetero"],
        "Kibenga": ["Gahwiji I", "Gahwiji II", "Kindonyi", "Murambi", "Ruhorobero", "Rwakaramira", "Rwarusaku"],
        "Kibirizi": ["Gacyamo", "Gahinga", "Gisenyi", "Gitera", "Kibirizi", "Rugazi", "Rwakibirizi"],
        "Mbyo": ["Cyaruhiririra", "Kabyo", "Rugarama", "Rwimikoni I", "Rwimikoni II"],
    },
    "Musenyi": {
        "Gicaca": ["Bidudu", "Cyanika", "Cyarubazi", "Gatare", "Gihari", "Kagusa", "Kamahango", "Kavumu", "Kidudu", "Migina", "Ngarama", "Remera", "Rusagara"],
        "Musenyi": ["Bidudu", "Bishinge", "Bizenga", "Cyeru", "Gakomeye", "Gakurazo", "Kigarama", "Kijuri", "Kiringa", "Muhanga", "Nunga", "Nyagasagara", "Rugando", "Rugeyo"],
        "Nyagihunika": ["Gatoki", "Gitagata", "Kigusa", "Kiruhura", "Mbonwa", "Nyakajuri", "Rugarama", "Rushubi", "Rwankeri"],
        "Rulindo": ["Kabeza", "Kabuye", "Kagunga", "Kanyamata", "Karambo", "Karubanzangabo", "Kinyovi", "Nyamuri", "Rulindo", "Runyonza"],
    },
    "Mwogo": {
        "Bitaba": ["Bitaba", "Gatwe", "Gisasa", "Misatsi", "Rebero", "Rukoronko"],
        "Kagasa": ["Gatare", "Gisenyi", "Karutabana", "Ngando", "Rubumba", "Rwintenderi"],
        "Rugunga": ["Kagerero", "Nyamabuye", "Nyarukombe", "Rugazi", "Rukira", "Rukore", "Rusagara"],
        "Rurenge": ["Gatoki", "Gitaraga", "Kaboshya", "Kaziramire", "Rurenge", "Rwabashenyi"],
    },
    "Ngeruka": {
        "Gihembe": ["Buhara", "Kabaya", "Kabuye", "Kadebu", "Kagasa", "Karambo", "Kirasaniro", "Kururama", "Nyakariba", "Nyarubande", "Rusagara", "Rutare", "Ruzinge", "Shitwe"],
        "Murama": ["Agashyamba", "Bishenyi", "Fatinkanda", "Gakurazo", "Gatanga", "Ikoni", "Kagege", "Kankuriyingoma", "Kigandu", "Kinamba", "Murama", "Muyange", "Nyakagarama", "Rusamaza", "Rwabisheshe", "Shami"],
        "Ngeruka": ["Binyonzwe", "Kamajeri", "Kamasonga", "Karugondo", "Kivugiza", "Muyange", "Ngeruka"],
        "Nyakayenzi": ["Heru", "Kabuye", "Karama", "Kavumu", "Kibaya", "Kibungo", "Kimiduha", "Murambi", "Nyakayenzi", "Twimpara"],
        "Rutonde": ["Akajuri", "Kabare", "Kabumbwe", "Kagano", "Kamugera", "Kamugore", "Kigarama", "Rubirizi", "Rugazi", "Runyonza", "Rusibya"],
    },
    "Ntarama": {
        "Cyugaro": ["Gatoro", "Kayenzi", "Kidudu", "Kingabo", "Rubomborana", "Rugarama", "Rugunga"],
        "Kanzenze": ["Cyeru", "Gasagara", "Kabaha", "Kabeza", "Karumuna", "Kurugenge", "Nyamabuye", "Rwangara"],
        "Kibungo": ["Kagoma I", "Kagoma II", "Kiganwa", "Nganwa", "Nyarunazi", "Ruhengeri", "Rusekera"],
    },
    "Nyamata": {
        "Kanazi": ["Bihari", "Cyeru", "Gitovu", "Kagirazina", "Musagara", "Nyarugati I", "Nyarugati II", "Rugando", "Sumbure"],
        "Kayumba": ["Gatare", "Karambi", "Kayenzi", "Murambi", "Nyagatovu", "Nyakwibereka", "Nyiramatuntu", "Rwanza"],
        "Maranyundo": ["Gahembe", "Gisunzu", "Mukoma", "Muyange", "Rugarama", "Rusagara"],
        "Murama": ["Bishweshwe", "Gataraga", "Gatare", "Kasebigege", "Kivugiza", "Kiyogoma", "Mwesa", "Rucucu", "Ruhanga", "Rutobotobo", "Rutukura"],
        "Nyamata y' Umujyi": ["Gasenga I", "Gasenga II", "Gatare I", "Gatare II", "Gatare III", "Nyabivumu", "Nyamata I", "Nyamata II", "Rugarama I", "Rugarama II", "Rugarama III", "Rwakibirizi I", "Rwakibirizi II"],
    },
    "Nyarugenge": {
        "Gihinga": ["Mabanga", "Mwoshya", "Ntungamo", "Nyabuhoro", "Nyagasozi", "Nyarubande", "Rwabusoro"],
        "Kabuye": ["Cyahafi", "Gateko", "Gatoki", "Karubagazi", "Nyakabingo", "Nyakabuye", "Nyarusambu"],
        "Murambi": ["Cundaminega", "Cyeru", "Kadogori", "Kanombe", "Kayitanga", "Nyagakombe", "Rugandara", "Rurama", "Rushorezo"],
        "Ngenda": ["Bushonyi", "Kamabare", "Kamugera", "Kiyovu", "Muyange", "Nyagisenyi", "Rubona", "Rugasa", "Rwashangwe", "Tubumba"],
        "Rugando": ["Bushenyi", "Gako", "Kamahirwe", "Nsoro", "Rebero", "Rugero"],
    },
    "Rilima": {
        "Kabeza": ["Bidenge", "Biraro", "Bwiza", "Gako", "Gasarwe", "Gasave", "Gitega", "Kabeza", "Kagarama", "Karambi", "Karambo", "Karirisi", "Marembo", "Nyamisagara"],
        "Karera": ["Gakurazo", "Gatare", "Kamahoro", "Mutarama", "Ruyenzi", "Rwankomati", "Rwavuningoma", "Rwimirama"],
        "Kimaranzara": ["Akintwari", "Akumunezero", "Amizero", "Buhoro", "Byimana", "Gasabo", "Gihushi", "Akabahaya", "Kidogo", "Kimaranzara", "Kivumu"],
        "Ntarama": ["Akabeza", "Gasave", "Gaseke", "Gasenyi", "Gitovu", "Kagugu", "Kamashya", "Kavumu", "Ntarama", "Nyamure", "Rurambo", "Saruduha"],
        "Nyabagendwa": ["Cyoma", "Gicaca", "Kamabuye", "Karama", "Mataba", "Mubuga", "Mukoma", "Murambi", "Nyabagendwa", "Nyamizi", "Rwibikara"],
    },
    "Ruhuha": {
        "Bihari": ["Bihari", "Busasamana", "Masenga I", "Masenga II", "Mukoma", "Nyagafunzo", "Rugarama", "Rwanzunga"],
        "Gatanga": ["Butereri", "Kayigi", "Kibaza", "Nyaburiba", "Nyakagarama", "Rwanika"],
        "Gikundamvura": ["Gikundamvura", "Kanombe", "Kazabagarura", "Kiyovu", "Rukurazo", "Rusenyi"],
        "Kindama": ["Gatare", "Gatovu", "Kagasera", "Kamweru", "Kibaza", "Kindama", "Rebero", "Ruramba", "Rutare", "Saruduha"],
        "Ruhuha": ["Kimikamba", "Mubano", "Nyabaranga", "Ruhuha I", "Ruhuha II"],
    },
    "Rweru": {
        "Batima": ["Agahonnyo", "Batima", "Gasororo", "Gikoma", "Ihara", "Kamudusi", "Mbuganzeri", "Rubira", "Ruhehe", "Twinyange"],
        "Kintambwe": ["Gakindo", "Gasenyi", "Maburane", "Mugina", "Nyiragiseke", "Nyirakanemba", "Nyirarubomboza", "Nzangwa", "Ubukoroco"],
        "Mazane": ["Gasasa", "Rukira", "Rusenyi"],
        "Nemba": ["Kigina", "Kimpara", "Kimvubu", "Muyoboro", "Nemba", "Nyakabingo", "Rutete", "Rwibinyogote", "Rwiminazi"],
        "Nkanga": ["Agashoro", "Kivusha", "Mujwiri", "Mushyoroti", "Nkanga", "Ruzo"],
        "Sharita": ["Karizinge", "Sharita"],
    },
    "Shyara": {
        "Kabagugu": ["Kabagugu", "Kinteko", "Ngaruye", "Rwamanyoni"],
        "Kamabuye": ["Gakoni", "Nyabaguma", "Rubwirwa"],
        "Nziranziza": ["Gahosha", "Kagarama", "Nziranziza", "Ruli"],
        "Rebero": ["Gateko", "Nyamirama", "Rebero", "Rutebe"],
        "Rutare": ["Gaseke", "Kamweru", "Ruhanga", "Rutare", "Shyara"],
    },
}

BUGESERA_SECTOR_CHOICES = [("", "Select Sector")] + [(s, s) for s in sorted(BUGESERA_SECTORS)]


def cells_for_sector(sector):
    return sorted(BUGESERA_SECTORS.get(sector, {}))


def villages_for_cell(sector, cell):
    return BUGESERA_SECTORS.get(sector, {}).get(cell, [])


def all_cell_choices():
    """Every cell name across all sectors, deduplicated, for populating a
    WTForms SelectField with a valid choice set before we know which sector
    the user picked. The real "does this cell belong to this sector" check
    happens in RegistrationForm.validate_cell."""
    seen = []
    for sector in sorted(BUGESERA_SECTORS):
        for cell in sorted(BUGESERA_SECTORS[sector]):
            if cell not in seen:
                seen.append(cell)
    return [("", "Select Cell")] + [(c, c) for c in seen]


def all_village_choices():
    """Every village name across the whole district, deduplicated (village
    names repeat across different cells), for the same reason as
    all_cell_choices(): a valid static choice set for WTForms, with the real
    "does this village belong to this cell" check done in
    RegistrationForm.validate_village."""
    seen = []
    for sector in BUGESERA_SECTORS:
        for cell in BUGESERA_SECTORS[sector]:
            for village in BUGESERA_SECTORS[sector][cell]:
                if village not in seen:
                    seen.append(village)
    return [("", "Select Village")] + [(v, v) for v in sorted(seen)]
