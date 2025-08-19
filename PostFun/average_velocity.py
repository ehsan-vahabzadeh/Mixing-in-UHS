
import os
import pyvista as pv
import numpy as np
import json
import xml.etree.ElementTree as ET

import warnings
def read_times_from_pvd(pvd_path):
    """Reads all timesteps from a .pvd file."""
    tree = ET.parse(pvd_path)
    root = tree.getroot()

    times = []
    for dataset in root.findall(".//DataSet"):
        t = dataset.attrib.get("timestep", None)
        if t is not None:
            times.append(float(t))
    return np.array(times)

def average_velocity_at_all_injection_ends(base_directory, pvd_directory, h2_threshold=0.01):
    results = []

    for folder_name in sorted(os.listdir(base_directory)):
        folder_path = os.path.join(base_directory, folder_name)
        if not os.path.isdir(folder_path):
            continue

        if folder_name == "H2-1e5-14-500-150":
            check  = 1
        # Parse cycle length from folder name
        parts = folder_name.split("-")
        try:
            cycle_length = float(parts[2])
        except (ValueError, IndexError):
            print(f"Skipping {folder_name}: cannot parse cycle length.")
            continue

        # Locate the PVD file in the separate pvd_directory
        pvd_file_path = os.path.join(pvd_directory, folder_name + ".pvd")
        if not os.path.exists(pvd_file_path):
            print(f"Skipping {folder_name}: PVD file not found: {pvd_file_path}")
            continue

        # Read times from the PVD file
        times = read_times_from_pvd(pvd_file_path)
        if len(times) == 0:
            print(f"Skipping {folder_name}: no times found in PVD.")
            continue

        # Compute target times for end-of-injection in 10 cycles
        if len(parts) > 5:
            CG = float(parts[-1])
        else:
            CG = 0.0
        
        end_injection_times = np.array([CG * (cycle_length / 2) + ((2 * n - 1) * cycle_length / 2) for n in range(1, 11)]) * 86400

        # Find closest indices in time array
        indices_of_interest = []
        for t_target in end_injection_times:
            idx = np.argmin(np.abs(times - t_target))
            indices_of_interest.append(idx)

        # Remove duplicates
        indices_of_interest = sorted(set(indices_of_interest))
        # Get sorted VTU files
        vtu_files = sorted([f for f in os.listdir(folder_path) if f.endswith('.vtu')])

        injection_end_data = []
        target_point_index = None
        Z_max = 60
        max_y = 0.0
        for idx in indices_of_interest:
            if idx >= len(vtu_files):
                continue
            file_path = os.path.join(folder_path, vtu_files[idx])
            try:
                mesh = pv.read(file_path)
                if mesh.n_points == 0 or 'velocity_gas (m/s)' not in mesh.point_data:
                    continue

                if target_point_index is None:
                    coords = mesh.points
                    max_y = np.max(coords[:, 1])
                    candidates = np.where(coords[:, 1] == max_y)[0]
                    min_x_idx = candidates[np.argmin(coords[candidates, 0])]
                    target_point_index = min_x_idx
                    # coords = mesh.cell_centers().points
                    # max_y = np.max(coords[:, 1])
                    # candidates = np.where(coords[:, 1] == max_y)[0]
                    # min_x_idx = candidates[np.argmin(coords[candidates, 0])]
                    # target_point_index = min_x_idx
                vx_current = float(mesh.point_data['velocity_gas (m/s)'][target_point_index, 0])
                file_path_temp = os.path.join(folder_path, vtu_files[1])
                mesh_temp = pv.read(file_path_temp)
                p_max = float(mesh_temp.point_data['p'][target_point_index])
                if 'x^H2_gas' in mesh.point_data:
                    mesh = mesh.point_data_to_cell_data()
                    coords = mesh.cell_centers().points
                    vx_all = mesh.cell_data['velocity_gas (m/s)'][:, 0]
                    h2_fraction = mesh.cell_data['x^H2_gas']
                    if len(parts) > 5:
                        porosity = float(parts[6]) / 100
                    else:
                        porosity = 0.3
                    rho = mesh.cell_data['rho']

                    valid = h2_fraction > h2_threshold
                    valid_range = (h2_fraction > h2_threshold) & (h2_fraction < 0.99)

                    simga_rz = None
                    simga_rr = None
                    if np.any(valid_range):
                        M00 = np.sum(h2_fraction[valid_range] * porosity)
                        M10 = np.sum(h2_fraction[valid_range] * coords[valid_range, 0] * porosity)
                        M20 = np.sum(h2_fraction[valid_range] * (coords[valid_range, 0]) ** 2 * porosity)
                        M01 = np.sum(h2_fraction[valid_range] * coords[valid_range, 1] * porosity)
                        M11 = np.sum(h2_fraction[valid_range] * coords[valid_range, 0] * coords[valid_range, 1] * porosity)
                        XC = M10 / M00 if M00 != 0 else 0
                        ZC = M01 / M00 if M00 != 0 else 0
                        simga_rz = float(M11 / M00 - XC * ZC if M00 != 0 else 0)
                        simga_rr = float(M20 / M00 - XC ** 2 if M00 != 0 else 0)

                    avg_vx = None
                    avg_vx_z = None
                    avg_vx_z_rev = None
                    avg_vx_x_H2 = None
                    avg_vx_x_H2_rev = None
                    avg_mass_velocity = None
                    max_x_valid = None
                    tip_velocity = None

                    if np.any(valid):
                        avg_vx = float(np.mean(vx_all[valid]))
                        avg_vx_z = float(np.mean((coords[valid, 1] / Z_max) * vx_all[valid]))
                        avg_vx_z_rev = float(np.mean((1 - (coords[valid, 1] / Z_max)) * vx_all[valid]))
                        avg_vx_x_H2 = float(np.mean(h2_fraction[valid] * vx_all[valid]))
                        avg_vx_x_H2_rev = float(np.mean((1 - h2_fraction[valid]) * vx_all[valid]))
                        avg_mass_velocity = float(np.mean(vx_all[valid] * rho[valid]))
                        max_x_valid = float(np.max(coords[valid, 0]))
                        valid_indices = np.nonzero(valid)[0]
                        pos_in_filtered = np.argmax(coords[valid, 0])
                        check = coords[valid, 1]
                        y_in_filtered = max_y - np.min(coords[valid, 1])
                        max_id = valid_indices[pos_in_filtered]
                        tip_velocity = float(vx_all[max_id])
                        if tip_velocity is not None and tip_velocity < 0 and idx > 0:
                            prev_file_path = os.path.join(folder_path, vtu_files[idx - 1])
                            try:
                                prev_mesh = pv.read(prev_file_path)
                                prev_mesh = prev_mesh.point_data_to_cell_data()
                                prev_coords = prev_mesh.cell_centers().points
                                prev_vx_all = prev_mesh.cell_data['velocity_gas (m/s)'][:, 0]
                                prev_h2_fraction = prev_mesh.cell_data['x^H2_gas']
                                
                                prev_valid = prev_h2_fraction > h2_threshold
                                if np.any(prev_valid):
                                    avg_vx = float(np.mean(vx_all[valid]))
                                    avg_vx_z = float(np.mean((coords[valid, 1] / Z_max) * vx_all[valid]))
                                    avg_vx_z_rev = float(np.mean((1 - (coords[valid, 1] / Z_max)) * vx_all[valid]))
                                    avg_vx_x_H2 = float(np.mean(h2_fraction[valid] * vx_all[valid]))
                                    avg_vx_x_H2_rev = float(np.mean((1 - h2_fraction[valid]) * vx_all[valid]))
                                    avg_mass_velocity = float(np.mean(vx_all[valid] * rho[valid]))
                                    max_x_valid = float(np.max(coords[valid, 0]))
                                    valid_indices = np.nonzero(prev_valid)[0]
                                    pos_in_filtered = np.argmax(prev_coords[prev_valid, 0])
                                    max_id = valid_indices[pos_in_filtered]
                                    prev_tip_velocity = float(prev_vx_all[max_id])

                                    if prev_tip_velocity >= 0:
                                        tip_velocity = prev_tip_velocity  # Use previous value if valid
                                    else:
                                        warnings.warn(f"Peclet number still negative for {folder_name} at time {times[idx - 1]} and {times[idx]}. Skipping.")
                            except Exception as e:
                                warnings.warn(f"Failed to read or process previous step at {vtu_files[idx - 1]}: {e}")
                    
                    injection_end_data.append({
                        "time": float(times[idx]),
                        "tip_velocity": tip_velocity,
                        "avg_vx": avg_vx,
                        "max_x_valid": max_x_valid,
                        "simga_rz": simga_rz,
                        "simga_rr": simga_rr,
                        "avg_vx_z": avg_vx_z,
                        "avg_vx_z_rev": avg_vx_z_rev,
                        "avg_vx_x_H2": avg_vx_x_H2,
                        "avg_vx_x_H2_rev": avg_vx_x_H2_rev,
                        "avg_mass_velocity": avg_mass_velocity,
                        "vx_inlet": vx_current,
                        "height": y_in_filtered,
                        "max_pressure": p_max,
                    })

            except Exception as e:
                print(f"Skipping {file_path}: {e}")
                continue

        results.append({
            "label": folder_name,
            "cycle_length": cycle_length,
            "injection_end_data": injection_end_data
        })

    # Save results
    folder_tag = os.path.basename(base_directory)
    # output_filename = f"{folder_tag}_all_injection_ends.json"
    output_filename = f"{folder_tag}.json"
    with open(output_filename, "w") as f:
        json.dump(results, f, indent=2)

    print(f"Results saved to {output_filename}")
    return results


if __name__ == "__main__":
    base_dir = "Y:\\Mixing Results\\July\\H2-No CG\\"
    # base_dir = "Y:\\Mixing Results\\New May\\N2"
    # base_dir = "Y:\\Mixing Results\\June\\N2"
    pvd_dir = base_dir   # since your PVD files are stored in CH4 folder
    os.chdir(base_dir)
    results = average_velocity_at_all_injection_ends(base_dir, pvd_dir)
    for res in results:
        print(res["label"])
        for inj_data in res["injection_end_data"]:
            print(f"Time {inj_data['time']:.2f} s → avg vx = {inj_data['avg_vx']}")