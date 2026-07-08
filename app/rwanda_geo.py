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
