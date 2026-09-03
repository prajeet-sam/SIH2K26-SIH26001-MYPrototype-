from typing import Optional

import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder

from data.schemas.models import SlopeUnit


LITHOLOGY_CATEGORIES = {
    "granite": 0,
    "gneiss": 1,
    "schist": 2,
    "quartzite": 3,
    "sandstone": 4,
    "limestone": 5,
    "shale": 6,
    "mudstone": 7,
    "basalt": 8,
    "alluvium": 9,
    "residual_soil": 10,
    "mixed": 11,
}

SOIL_TYPE_CATEGORIES = {
    "clay": 0,
    "sandy_clay": 1,
    "silt": 2,
    "sandy_loam": 3,
    "gravelly_sand": 4,
    "laterite": 5,
    "peat": 6,
    "colluvium": 7,
    "residual": 8,
}

LANDCOVER_CATEGORIES = {
    "dense_forest": 0,
    "open_forest": 1,
    "shrubland": 2,
    "grassland": 3,
    "agriculture": 4,
    "bare_rock": 5,
    "bare_soil": 6,
    "built_up": 7,
    "water": 8,
    "wetland": 9,
}

_lithology_encoder: Optional[LabelEncoder] = None
_soil_encoder: Optional[LabelEncoder] = None
_landcover_encoder: Optional[LabelEncoder] = None


def encode_lithology(value: str) -> int:
    return LITHOLOGY_CATEGORIES.get(value.lower(), LITHOLOGY_CATEGORIES["mixed"])


def encode_soil_type(value: str) -> int:
    return SOIL_TYPE_CATEGORIES.get(value.lower(), SOIL_TYPE_CATEGORIES["residual"])


def encode_land_cover(value: str) -> int:
    return LANDCOVER_CATEGORIES.get(value.lower(), LANDCOVER_CATEGORIES["bare_soil"])


def encode_lithology_fitted(values: pd.Series) -> np.ndarray:
    global _lithology_encoder
    if _lithology_encoder is None:
        _lithology_encoder = LabelEncoder()
        _lithology_encoder.fit(values)
    return _lithology_encoder.transform(values)


def encode_soil_type_fitted(values: pd.Series) -> np.ndarray:
    global _soil_encoder
    if _soil_encoder is None:
        _soil_encoder = LabelEncoder()
        _soil_encoder.fit(values)
    return _soil_encoder.transform(values)


def encode_land_cover_fitted(values: pd.Series) -> np.ndarray:
    global _landcover_encoder
    if _landcover_encoder is None:
        _landcover_encoder = LabelEncoder()
        _landcover_encoder.fit(values)
    return _landcover_encoder.transform(values)


def prepare_feature_matrix(
    slopes: list[SlopeUnit],
    drainage_density: Optional[pd.Series] = None,
    lithology: Optional[pd.Series] = None,
    soil_type: Optional[pd.Series] = None,
    land_cover: Optional[pd.Series] = None,
) -> pd.DataFrame:
    records = []
    for slope in slopes:
        records.append(
            {
                "slope_id": slope.slope_id,
                "slope_angle": slope.slope_angle_deg,
                "elevation": slope.elevation_m,
                "aspect": slope.aspect_deg,
                "curvature": slope.curvature,
            }
        )
    df = pd.DataFrame(records).set_index("slope_id")

    if drainage_density is not None:
        df["drainage_density"] = drainage_density
    else:
        df["drainage_density"] = 0.0

    if lithology is not None:
        df["lithology_encoded"] = lithology.map(encode_lithology)
    else:
        df["lithology_encoded"] = 0

    if soil_type is not None:
        df["soil_type_encoded"] = soil_type.map(encode_soil_type)
    else:
        df["soil_type_encoded"] = 0

    if land_cover is not None:
        df["land_cover_encoded"] = land_cover.map(encode_land_cover)
    else:
        df["land_cover_encoded"] = 0

    df = df.reset_index()
    return df


def prepare_feature_matrix_from_dataframe(
    df: pd.DataFrame,
    slope_id_col: str = "slope_id",
) -> pd.DataFrame:
    output = pd.DataFrame()
    output["slope_id"] = df[slope_id_col]
    output["slope_angle"] = df["slope_angle_deg"]
    output["elevation"] = df["elevation_m"]
    output["aspect"] = df["aspect_deg"]
    output["curvature"] = df["curvature"]

    if "drainage_density" in df.columns:
        output["drainage_density"] = df["drainage_density"]
    else:
        output["drainage_density"] = 0.0

    if "lithology" in df.columns:
        output["lithology_encoded"] = df["lithology"].map(encode_lithology)
    else:
        output["lithology_encoded"] = 0

    if "soil_type" in df.columns:
        output["soil_type_encoded"] = df["soil_type"].map(encode_soil_type)
    else:
        output["soil_type_encoded"] = 0

    if "land_cover_class" in df.columns:
        output["land_cover_encoded"] = df["land_cover_class"].map(encode_land_cover)
    else:
        output["land_cover_encoded"] = 0

    return output


def build_label_vector(
    slopes: list[SlopeUnit],
    events: list[dict],
) -> pd.Series:
    event_slope_ids = {e["slope_id"] for e in events if e.get("slope_id")}
    labels = [1 if s.slope_id in event_slope_ids else 0 for s in slopes]
    return pd.Series(labels, index=[s.slope_id for s in slopes], name="label")


def build_label_vector_from_dataframe(
    slope_df: pd.DataFrame,
    event_df: pd.DataFrame,
    slope_id_col: str = "slope_id",
) -> pd.Series:
    event_slope_ids = set(event_df[slope_id_col].unique())
    labels = slope_df[slope_id_col].apply(lambda x: 1 if x in event_slope_ids else 0)
    labels.index = slope_df[slope_id_col]
    return labels
