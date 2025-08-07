import vtk
import os

def merge_vtu_files(input_directory, num_timesteps, num_parts):
    # Create a list to store the simulation names from the .pvd files
    pvd_files = [f for f in os.listdir(input_directory) if f.endswith('.pvd')]
    
    # Loop over each pvd file (each simulation)
    for pvd_file in pvd_files:
        # Extract the simulation name from the .pvd file
        simulation_name = os.path.splitext(pvd_file)[0]  # Remove extension
        
        # Create a folder for the merged data for this simulation
        output_directory = os.path.join(input_directory, simulation_name)
        
        # **Check if the folder exists and contains merged files**
        if os.path.exists(output_directory) and any(f.endswith('.vtu') for f in os.listdir(output_directory)):
            print(f"Skipping {simulation_name}, merged files already exist in {output_directory}.")
            continue  # Skip this simulation

        os.makedirs(output_directory, exist_ok=True)
        print(f"Processing simulation: {simulation_name}")
        
        for timestep in range(num_timesteps):
            appendFilter = vtk.vtkAppendFilter()

            # Loop through all parts (16 files per timestep)
            for part in range(num_parts):
                # Generate the file name for each part
                file_name = f"s{num_parts:04}-p{part:04}-{simulation_name}-{timestep:05}.vtu"
                file_path = os.path.join(input_directory, file_name)
                
                # Check if the file exists
                if not os.path.exists(file_path):
                    print(f"Warning: File {file_path} does not exist. Skipping this file.")
                    continue
                
                # Read the VTU file
                reader = vtk.vtkXMLUnstructuredGridReader()
                reader.SetFileName(file_path)
                reader.Update()

                # Add the grid to the append filter
                appendFilter.AddInputData(reader.GetOutput())

            # Combine all parts for the current timestep
            appendFilter.Update()

            # The output file should have the same name as the input file
            output_file_name = f"s{num_parts:04}-{simulation_name}-{timestep:05}.vtu"
            output_file_path = os.path.join(output_directory, output_file_name)

            # Create a writer to output the merged file
            writer = vtk.vtkXMLUnstructuredGridWriter()
            writer.SetFileName(output_file_path)
            writer.SetInputData(appendFilter.GetOutput())
            writer.Write()

            print(f"Merged file for timestep {timestep} written to {output_file_path}")

# **Usage Example**
input_dir = os.getcwd()  # Get current working directory
num_timesteps = 2201  # Adjust based on your simulation setup
num_parts = 16  # Adjust based on the number of parts per timestep

# Run the merging function
merge_vtu_files(input_dir, num_timesteps, num_parts)
