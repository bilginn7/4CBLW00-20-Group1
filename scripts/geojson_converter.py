from pathlib import Path
import geopandas as gpd
from collections.abc import Sequence, Callable

class GeoJSONConverter:
    """
    Converts a geojson file to a geoparquet file, defaulted to snappy compression.
    """
    def __init__(self, compression: str = 'snappy') -> None:
        self.compression = compression

    @staticmethod
    def _validate_input_path(input_path: str | Path) -> Path:
        """Validate and convert input path to Path object.

        :param input_path: Location of input geojson file.
        :return: Path object.
        """
        if not Path(input_path).exists():
            raise FileNotFoundError(f"Input path {input_path} does not exist.")
        if not Path(input_path).suffix.lower() == ".geojson":
            raise ValueError(f"Input path {input_path} is not a geojson file.")
        return Path(input_path)

    @staticmethod
    def _generate_output_path(input_path: Path, output_path: str | Path | None = None,
                            rename_func: Callable[[str], str] | None = None) -> Path:
        """Generate output path with optional renaming.

        :param input_path: Location of input geojson file.
        :param output_path: Location of output geoparquet file.
        :return: Path object.
        """
        if output_path is None:
            new_name = input_path.stem
            if rename_func:
                new_name = rename_func(new_name)
            return input_path.parent / f"{new_name}.geoparquet"

        output = Path(output_path)
        if output.is_dir():
            new_name = input_path.stem
            if rename_func:
                new_name = rename_func(new_name)
            return output / f"{new_name}.geoparquet"
        return output

    @staticmethod
    def _ensure_output_directory(output_path: Path) -> None:
        """Create output directory if it doesn't exist."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _load_geojson(input_path: Path) -> gpd.GeoDataFrame:
        """Load GeoJSON file into GeoDataFrame."""
        return gpd.read_file(input_path)

    def _save_geoparquet(self, gdf: gpd.GeoDataFrame, output_path: Path) -> None:
        """Save GeoDataFrame as GeoParquet file."""
        gdf.to_parquet(output_path, compression=self.compression)

    def convert(self, input_path: str | Path, output_path: str | Path | None = None,
                rename_func: Callable[[str], str] | None = None) -> Path:
        """Convert GeoJSON file to GeoParquet format."""
        input_path_obj = self._validate_input_path(input_path)
        output_path_obj = self._generate_output_path(input_path_obj, output_path, rename_func)

        self._ensure_output_directory(output_path_obj)

        gdf = self._load_geojson(input_path_obj)
        self._save_geoparquet(gdf, output_path_obj)

        return output_path_obj


if __name__ == "__main__":
    # Create converter with default compression
    converter = GeoJSONConverter()

    # Data locations
    LAD_FILE: str = '../data/geo/Local_Authority_Districts_May_2022_UK_BGC_V3_2022_-201744063594132452.geojson'
    WARD_FILE: str = '../data/geo/Wards_December_2024_Boundaries_UK_BGC_-2654605954884295357.geojson'
    LSOA_FILE: str = '../data/geo/Lower_layer_Super_Output_Areas_December_2021_Boundaries_EW_BGC_V5_-7764840717091613250.geojson'
    FILES: Sequence[str] = [LAD_FILE, WARD_FILE, LSOA_FILE]
    OUTPUT_NAMES: Sequence[str] = ['LAD_shape', 'WARD_shape', 'LSOA_shape']

    # Conversion
    for index, file in enumerate(FILES):
        converter.convert(
            input_path=file,
            rename_func=lambda _: OUTPUT_NAMES[index])

    print(f"Converted {len(FILES)} files")