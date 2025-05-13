import os
import gdown


# List of OSRM files with their Google Drive file IDs
OSRM_FILES = [
    {"name": "united-kingdom-latest.osrm", "id": "1UyXWdCN826qDrV-NzuWACfPF0arQp2FQ"},
    {"name": "united-kingdom-latest.osrm.cells", "id": "1jdnJGetEIV6vhaXhXQIu6gjAajb7u48L"},
    {"name": "united-kingdom-latest.osrm.cell_metrics", "id": "1jnjFfmnK_w5LHXGOtyw07GdOs-hjThAU"},
    {"name": "united-kingdom-latest.osrm.cnbg", "id": "1NZwkO6k-G-UhCjkjbq0SUyfQhYyVsEXp"},
    {"name": "united-kingdom-latest.osrm.cnbg_to_ebg", "id": "1sKelefHfRo8X75ZDBXHqk8XMDg39JOu8"},
    {"name": "united-kingdom-latest.osrm.datasource_names", "id": "1wJ_vL7TkBx8vMoFzy5Z5GQXcuSZaoSSJ"},
    {"name": "united-kingdom-latest.osrm.ebg", "id": "1ZZ4QNcT-N_GVvzERvcZh1wkbqas4nokz"},
    {"name": "united-kingdom-latest.osrm.ebg_nodes", "id": "1oPnkfC5Aimjw4wLvWdtD-b9_whKy97qI"},
    {"name": "united-kingdom-latest.osrm.edges", "id": "1bB0IrsDd3cggKfR1Mrq4SDaFOH7x4xfc"},
    {"name": "united-kingdom-latest.osrm.enw", "id": "1NhmCQoCK2K3eklJcHrCH5AFAHzsmX9NY"},
    {"name": "united-kingdom-latest.osrm.fileIndex", "id": "1PEcZ81Xa3C8WuI1_QIN8842xDOWigCTe"},
    {"name": "united-kingdom-latest.osrm.geometry", "id": "1uuk7GncDhykX4uWeY15nMQf9H9s4mTgu"},
    {"name": "united-kingdom-latest.osrm.icd", "id": "1M2YhRZEwFszse6GJ9kW9RLnjPWtjoOqj"},
    {"name": "united-kingdom-latest.osrm.maneuver_overrides", "id": "1R-jeRnVVn1gpMsPL3l3BwHypSVdt-VKw"},
    {"name": "united-kingdom-latest.osrm.mldgr", "id": "1MRtmw_enF5S8BHJfy5cihIba4-8-LGd_"},
    {"name": "united-kingdom-latest.osrm.names", "id": "1i0pq4JBq9-68EbSH43D6i3iu_Gui8xnF"},
    {"name": "united-kingdom-latest.osrm.nbg_nodes", "id": "1HyyId2sUwfkpURiGt9phmOwAtLe9hN_p"},
    {"name": "united-kingdom-latest.osrm.partition", "id": "17txuT3PNCjUfV6e41gXaT2IKOH6H3yiF"},
    {"name": "united-kingdom-latest.osrm.properties", "id": "1aMqdkJJ0wcI7IXSuqApTyts-8V8ZOX1D"},
    {"name": "united-kingdom-latest.osrm.ramIndex", "id": "1h5wsTIqaaCKiU76SF3tXVsxDeej0Y11I"},
    {"name": "united-kingdom-latest.osrm.restrictions", "id": "1urme6HMSufMvmgRrnL3qoFOWLUu6yG27"},
    {"name": "united-kingdom-latest.osrm.timestamp", "id": "1ek3TwXBKLw1Iqmy_I7HryxcF5LA_NHXO"},
    {"name": "united-kingdom-latest.osrm.tld", "id": "1cVMfjnUKAK3HEH8MrgTAyzufobMOfEty"},
    {"name": "united-kingdom-latest.osrm.tls", "id": "13FoEHR2ublLla-OY8voDieu4BYxwVjVe"},
    {"name": "united-kingdom-latest.osrm.turn_duration_penalties", "id": "1_w3ICLqL2wRNahVbNiKiSNk22-nFn8ib"},
    {"name": "united-kingdom-latest.osrm.turn_penalties_index", "id": "1qcUKNRkidRtuUnOZViD8Oy0QlsHfYDCz"},
    {"name": "united-kingdom-latest.osrm.turn_weight_penalties", "id": "1QjehAuF_p2UEM1ZxPBZ4M6VYZSimFVwd"},
    {"name": "united-kingdom-latest.osm.pbf", "id": "1J7fe4KKK-6Dhn2uOyXGuyvw72-s7mmTK"}
]

def download_file(file_id, file_name, destination_dir):
    """Download a file from Google Drive by ID."""
    url = f"https://drive.google.com/drive/folders/1codRfCAnWerjREciJfr0ZxM9rCalyUVX?usp=sharing"
    output = os.path.join(destination_dir, file_name)
    gdown.download(url, output, quiet=False)
    print(f"Downloaded {file_name} to {output}")

def main():
    # Ensure osrm/ directory exists
    osrm_dir = "osrm"
    os.makedirs(osrm_dir, exist_ok=True)

    # Download each file
    for file in OSRM_FILES:
        download_file(file["id"], file["name"], osrm_dir)

if __name__ == "__main__":
    main()