import base64
from typing import Any, Dict, List, Optional, Tuple

import datetime
import hashlib
import json
import os
import time
import uuid
from collections import OrderedDict
import logging

from dateutil.tz import tzlocal
from tqdm import tqdm

from . import ipc
from . import uploader
from .error import print_error
from .exif_read import ExifRead
from .exif_write import ExifEdit
from .geo import (
    normalize_bearing,
    interpolate_lat_lon,
    gps_distance,
    MapillaryInterpolationError,
)
from .gps_parser import get_lat_lon_time_from_gpx, get_lat_lon_time_from_nmea
from .gpx_from_blackvue import gpx_from_blackvue
from .gpx_from_exif import gpx_from_exif
from .gpx_from_gopro import gpx_from_gopro
from .utils import force_decode

"""
auxillary processing functions
"""


LOG = logging.getLogger()


def geotag_from_exif(
    process_file_list: List[str],
    import_path: str,
    offset_time: float = 0.0,
    offset_angle: float = 0.0,
    verbose: bool = False,
) -> None:
    if offset_time == 0:
        for image in tqdm(
            process_file_list, desc="Extracting gps data from image EXIF"
        ):
            geotag_properties = get_geotag_properties_from_exif(
                image, offset_angle, verbose
            )

            create_and_log_process(
                image, "geotag_process", "success", geotag_properties, verbose
            )
    else:
        try:
            geotag_source_path = gpx_from_exif(process_file_list, import_path, verbose)
            if not geotag_source_path or not os.path.isfile(geotag_source_path):
                raise Exception
        except Exception as e:
            print_error(
                f"Error, failed extracting data from exif due to {e}, exiting..."
            )
            raise e

        geotag_from_gps_trace(
            process_file_list,
            "gpx",
            geotag_source_path,
            offset_time,
            offset_angle,
            verbose=verbose,
        )


def get_geotag_properties_from_exif(
    image: str, offset_angle: float = 0.0, verbose: bool = False
) -> Optional[Dict]:
    try:
        exif = ExifRead(image)
    except:
        print_error(
            "Error, EXIF could not be read for image "
            + image
            + ", geotagging process failed for this image since gps/time properties not read."
        )
        return None
    # required tags
    try:
        lon, lat = exif.extract_lon_lat()
    except:
        print_error(
            "Error, "
            + image
            + " image latitude or longitude tag not in EXIF. Geotagging process failed for this image, since this is required information."
        )
        return None
    if lat is not None and lon is not None:
        geotag_properties: Dict = {
            "MAPLatitude": lat,
            "MAPLongitude": lon,
        }
    else:
        print_error(
            "Error, "
            + image
            + " image latitude or longitude tag not in EXIF. Geotagging process failed for this image, since this is required information."
        )
        return None
    try:
        timestamp = exif.extract_capture_time()
        if timestamp is None:
            raise Exception
    except:
        print_error(
            "Error, "
            + image
            + " image capture time tag not in EXIF. Geotagging process failed for this image, since this is required information."
        )
        return None

    try:
        geotag_properties["MAPCaptureTime"] = datetime.datetime.strftime(
            timestamp, "%Y_%m_%d_%H_%M_%S_%f"
        )[:-3]
    except:
        print_error(
            f"Error, {image} image capture time tag incorrect format. Geotagging process failed for this image, since this is required information."
        )
        return None

    # optional fields
    try:
        geotag_properties["MAPAltitude"] = exif.extract_altitude()
    except:
        if verbose:
            print("Warning, image altitude tag not in EXIF.")
    try:
        heading = exif.extract_direction()
        if heading is None:
            heading = 0.0
        heading = normalize_bearing(heading + offset_angle)
        # bearing of the image
        geotag_properties["MAPCompassHeading"] = {
            "TrueHeading": heading,
            "MagneticHeading": heading,
        }
    except:
        if verbose:
            print("Warning, image direction tag not in EXIF.")

    return geotag_properties


def geotag_from_gopro_video(
    process_file_list,
    import_path,
    geotag_source_path,
    offset_time,
    offset_angle,
    local_time,
    sub_second_interval,
    use_gps_start_time=False,
    verbose=False,
):
    if geotag_source_path is None:
        raise RuntimeError(
            f"A path to your video directory is required to be specified in --geotag_source_path",
        )

    if not os.path.isdir(geotag_source_path):
        raise RuntimeError(
            f"The path specified in geotag_source_path {geotag_source_path} is not a directory"
        )

    # for each video, create gpx trace and geotag the corresponding video
    # frames
    gopro_videos = uploader.get_video_file_list(geotag_source_path)
    for gopro_video in gopro_videos:
        gopro_video_filename, _ = os.path.splitext(os.path.basename(gopro_video))
        gpx_path = gpx_from_gopro(gopro_video)

        process_file_sublist = [
            x
            for x in process_file_list
            if os.path.join(gopro_video_filename, gopro_video_filename + "_") in x
        ]

        if not process_file_sublist:
            print_error(
                f"Error, no video frames extracted for video file {gopro_video} in import_path {import_path}"
            )
            create_and_log_process_in_list(
                process_file_sublist, "geotag_process", "failed", verbose=verbose
            )
            continue

        geotag_from_gps_trace(
            process_file_sublist,
            "gpx",
            gpx_path,
            offset_time,
            offset_angle,
            local_time,
            sub_second_interval,
            use_gps_start_time,
            verbose,
        )


def geotag_from_blackvue_video(
    process_file_list,
    import_path,
    geotag_source_path,
    offset_time,
    offset_angle,
    local_time,
    sub_second_interval,
    use_gps_start_time=False,
    verbose=False,
):
    if geotag_source_path is None:
        raise RuntimeError(
            f"A path to your video directory is required to be specified in --geotag_source_path",
        )

    if not os.path.isdir(geotag_source_path):
        raise RuntimeError(
            f"The path specified in --geotag_source_path {geotag_source_path} is not a directory"
        )

    # for each video, create gpx trace and geotag the corresponding video
    # frames
    blackvue_videos = uploader.get_video_file_list(geotag_source_path)
    for blackvue_video in blackvue_videos:
        blackvue_video_filename = (
            os.path.basename(blackvue_video).replace(".mp4", "").replace(".MP4", "")
        )
        [gpx_path, is_stationary_video] = gpx_from_blackvue(
            blackvue_video, use_nmea_stream_timestamp=False
        )

        if not gpx_path or not os.path.isfile(gpx_path):
            raise RuntimeError(f"Error, GPX path {gpx_path} not found")

        if is_stationary_video:
            print_error("Warning: Skipping stationary video")
            continue

        process_file_sublist = [
            x
            for x in process_file_list
            if os.path.join(blackvue_video_filename, blackvue_video_filename + "_") in x
        ]

        if not len(process_file_sublist):
            print_error(
                f"Error, no video frames extracted for video file {blackvue_video} in import_path {import_path}"
            )
            create_and_log_process_in_list(
                process_file_sublist, "geotag_process", "failed", verbose=verbose
            )
            continue

        geotag_from_gps_trace(
            process_file_sublist,
            "gpx",
            gpx_path,
            offset_time,
            offset_angle,
            local_time,
            sub_second_interval,
            use_gps_start_time,
            verbose,
        )


def geotag_from_gps_trace(
    process_file_list,
    geotag_source,
    geotag_source_path,
    offset_time=0.0,
    offset_angle=0.0,
    local_time=False,
    sub_second_interval=0.0,
    use_gps_start_time=False,
    verbose=False,
):
    if geotag_source == "gpx":
        file_desc = "a GPX file"
    elif geotag_source == "nmea":
        file_desc = "an NMEA file"
    else:
        raise RuntimeError(f"Invalid geotag source {geotag_source}")

    if geotag_source_path is None:
        raise RuntimeError(
            f"{file_desc} is required to be specified in --geotag_source_path",
        )

    if not os.path.isfile(geotag_source_path):
        raise RuntimeError(
            f"The path specified in geotag_source_path {geotag_source_path} is not {file_desc}"
        )

    # print time now to warn in case local_time
    if local_time:
        now = datetime.datetime.now(tzlocal())
        print(
            f"Your local timezone is {now.strftime('%Y-%m-%d %H:%M:%S %Z')}. If not, the geotags will be wrong."
        )
    else:
        # if not local time to be used, warn UTC will be used
        print(
            "It is assumed that the image timestamps are in UTC. If not, try using the option --local_time."
        )

    # read gps file to get track locations
    if geotag_source == "gpx":
        gps_trace = get_lat_lon_time_from_gpx(geotag_source_path, local_time)
    elif geotag_source == "nmea":
        gps_trace = get_lat_lon_time_from_nmea(geotag_source_path, local_time)
    else:
        raise RuntimeError(f"Invalid geotag source {geotag_source}")

    if not gps_trace:
        print_error(
            f"Error, gps trace file {geotag_source_path} was not read, images can not be geotagged."
        )
        create_and_log_process_in_list(
            process_file_list, "geotag_process", "failed", verbose=verbose
        )
        return

    pairs = [(ExifRead(f).extract_capture_time(), f) for f in process_file_list]

    if use_gps_start_time:
        filtered_pairs: List[Tuple[datetime.datetime, str]] = [
            p for p in pairs if p[0] is not None
        ]
        sorted_pairs = sorted(filtered_pairs)
        if sorted_pairs:
            # update offset time with the gps start time
            offset_time += (sorted_pairs[0][0] - gps_trace[0][0]).total_seconds()
            LOG.info(
                f"Use GPS start time, which is same as using offset_time={offset_time}"
            )

    for capture_time, image in tqdm(
        pairs,
        desc="Inserting gps data into image EXIF",
    ):
        if capture_time is None:
            print_error(f"Error, capture time could not be extracted for image {image}")
            create_and_log_process(image, "geotag_process", "failed", verbose=verbose)
        else:
            try:
                geotag_properties = get_geotag_properties_from_gps_trace(
                    image, capture_time, gps_trace, offset_angle, offset_time
                )
            except MapillaryInterpolationError as ex:
                raise RuntimeError(
                    f"""Failed to interpolate image {image} with the geotag source file {geotag_source_path}. Try the following fixes:
1. Specify --local_time to read the timestamps from the geotag source file as local time
2. Use --use_gps_start_time to align the start time
3. Manually shift the timestamps in the geotag source file with --offset_time OFFSET_IN_SECONDS
"""
                ) from ex

            create_and_log_process(
                image, "geotag_process", "success", geotag_properties, verbose
            )


def get_geotag_properties_from_gps_trace(
    image,
    capture_time: datetime.datetime,
    gps_trace: list,
    offset_angle=0.0,
    offset_time=0.0,
) -> dict:
    capture_time = capture_time - datetime.timedelta(seconds=offset_time)

    lat, lon, bearing, elevation = interpolate_lat_lon(gps_trace, capture_time)

    geotag_properties = {
        "MAPLatitude": lat,
        "MAPLongitude": lon,
    }

    corrected_bearing = (bearing + offset_angle) % 360
    geotag_properties["MAPCompassHeading"] = {
        "TrueHeading": corrected_bearing,
        "MagneticHeading": corrected_bearing,
    }

    geotag_properties["MAPCaptureTime"] = datetime.datetime.strftime(
        capture_time, "%Y_%m_%d_%H_%M_%S_%f"
    )[:-3]

    if elevation is not None:
        geotag_properties["MAPAltitude"] = elevation

    return geotag_properties


def get_upload_param_properties(
    log_root: str,
    image: str,
    user_name: str,
    user_upload_token: str,
    user_key: str,
    verbose: bool = False,
) -> Optional[Dict]:
    if not os.path.isdir(log_root):
        print(
            "Warning, sequence process has not been done for image "
            + image
            + ", therefore it will not be included in the upload params processing."
        )
        return None

    # check if geotag process was a success
    log_sequence_process_success = os.path.join(log_root, "sequence_process_success")
    if not os.path.isfile(log_sequence_process_success):
        print(
            "Warning, sequence process failed for image "
            + image
            + ", therefore it will not be included in the upload params processing."
        )
        return None

    upload_params_process_success_path = os.path.join(
        log_root, "upload_params_process_success"
    )

    # load the sequence json
    user_process_json_path = os.path.join(log_root, "user_process.json")
    try:
        user_data = load_json(user_process_json_path)
    except:
        print(
            f"Warning, user data not read for image {image}, therefore it will not be included in the upload params processing."
        )
        return None

    if "MAPSettingsUserKey" not in user_data:
        print(
            "Warning, user key not in user data for image {image}, therefore it will not be included in the upload params processing."
        )
        return None

    user_key = user_data["MAPSettingsUserKey"]
    organization_key = user_data.get("MAPOrganizationKey")
    private = user_data.get("MAPPrivate", False)

    # load the sequence json
    sequence_process_json_path = os.path.join(log_root, "sequence_process.json")
    try:
        sequence_data = load_json(sequence_process_json_path)
    except:
        print(
            "Warning, sequence data not read for image "
            + image
            + ", therefore it will not be included in the upload params processing."
        )
        return None

    if "MAPSequenceUUID" not in sequence_data:
        print(
            "Warning, sequence uuid not in sequence data for image "
            + image
            + ", therefore it will not be included in the upload params processing."
        )
        return None

    sequence_uuid = sequence_data["MAPSequenceUUID"]

    upload_params = {
        "key": sequence_uuid,
        "sequence_uuid": sequence_uuid,
        "user_key": user_key,
        "user_name": user_name,
        "organization_key": organization_key,
        "private": private,
    }

    x = base64.b64encode(image.encode("utf-8")).decode("utf-8")
    s = f"{user_upload_token}{user_key}{x}"
    settings_upload_hash = hashlib.sha256(s.encode("utf-8")).hexdigest()
    save_json(
        {"MAPSettingsUploadHash": settings_upload_hash},
        os.path.join(log_root, "settings_upload_hash.json"),
    )
    return upload_params


def get_final_mapillary_image_description(
    log_root: str,
    image: str,
    master_upload: bool = False,
    verbose: bool = False,
    skip_EXIF_insert: bool = False,
    keep_original: bool = False,
    overwrite_all_EXIF_tags: bool = False,
    overwrite_EXIF_time_tag: bool = False,
    overwrite_EXIF_gps_tag: bool = False,
    overwrite_EXIF_direction_tag: bool = False,
    overwrite_EXIF_orientation_tag: bool = False,
) -> Optional[Dict]:
    sub_commands = [
        "user_process",
        "geotag_process",
        "sequence_process",
        "upload_params_process",
        "settings_upload_hash",
        "import_meta_data_process",
    ]
    final_mapillary_image_description = {}

    for sub_command in sub_commands:
        sub_command_status = os.path.join(log_root, sub_command + "_failed")

        if (
            os.path.isfile(sub_command_status)
            and sub_command != "import_meta_data_process"
        ):
            LOG.warning(
                f"Warning, required {sub_command} failed for image {image}",
                exc_info=True,
            )
            return None

        sub_command_data_path = os.path.join(log_root, sub_command + ".json")
        if (
            not os.path.isfile(sub_command_data_path)
            and sub_command != "import_meta_data_process"
        ):
            if (
                sub_command == "settings_upload_hash"
                or sub_command == "upload_params_process"
            ) and master_upload:
                continue
            else:
                LOG.warning(
                    f"Warning, required {sub_command} did not result in a valid json file for image {image}",
                    exc_info=True,
                )
                return None
        if (
            sub_command == "settings_upload_hash"
            or sub_command == "upload_params_process"
        ):
            continue
        try:
            sub_command_data = load_json(sub_command_data_path)
            if not sub_command_data:
                if verbose:
                    LOG.warning(
                        f"Warning, no data read from json file {sub_command_data_path}",
                        exc_info=True,
                    )
                return None

            final_mapillary_image_description.update(sub_command_data)
        except Exception:
            if sub_command == "import_meta_data_process":
                LOG.warning(
                    "Warning, could not load json file " + sub_command_data_path,
                    exc_info=True,
                )
                continue
            else:
                LOG.warning(
                    "Warning, could not load json file " + sub_command_data_path,
                    exc_info=True,
                )
                return None

    # a unique photo ID to check for duplicates in the backend in case the
    # image gets uploaded more than once
    final_mapillary_image_description["MAPPhotoUUID"] = str(uuid.uuid4())

    if skip_EXIF_insert:
        return final_mapillary_image_description

    image_exif = ExifEdit(image)

    image_exif.add_image_description(final_mapillary_image_description)

    # also try to set time and gps so image can be placed on the map for testing and
    # qc purposes
    try:
        if overwrite_all_EXIF_tags or overwrite_EXIF_time_tag:
            image_exif.add_date_time_original(
                datetime.datetime.strptime(
                    final_mapillary_image_description["MAPCaptureTime"],
                    "%Y_%m_%d_%H_%M_%S_%f",
                )
            )

        if overwrite_all_EXIF_tags or overwrite_EXIF_gps_tag:
            image_exif.add_lat_lon(
                final_mapillary_image_description["MAPLatitude"],
                final_mapillary_image_description["MAPLongitude"],
            )

        if overwrite_all_EXIF_tags or overwrite_EXIF_direction_tag:
            image_exif.add_direction(
                final_mapillary_image_description["MAPCompassHeading"]["TrueHeading"]
            )

        if overwrite_all_EXIF_tags or overwrite_EXIF_orientation_tag:
            if "MAPOrientation" in final_mapillary_image_description:
                image_exif.add_orientation(
                    final_mapillary_image_description["MAPOrientation"]
                )
    except Exception:
        LOG.warning("Error overwriting EXIF", exc_info=True)

    filename_keep_original = processed_images_rootpath(image)
    if os.path.isfile(filename_keep_original):
        os.remove(filename_keep_original)

    if keep_original:
        if not os.path.isdir(os.path.dirname(filename_keep_original)):
            os.makedirs(os.path.dirname(filename_keep_original))
        target = filename_keep_original
    else:
        target = image

    image_exif.write(filename=target)

    return final_mapillary_image_description


def get_geotag_data(log_root: str, image: str, verbose: bool = False) -> Optional[Dict]:
    if not os.path.isdir(log_root):
        if verbose:
            print("Warning, no logs for image " + image)
        return None

    # check if geotag process was a success
    log_geotag_process_success = os.path.join(log_root, "geotag_process_success")
    if not os.path.isfile(log_geotag_process_success):
        print(
            "Warning, geotag process failed for image "
            + image
            + ", therefore it will not be included in the sequence processing."
        )
        return None
    # load the geotag json
    geotag_process_json_path = os.path.join(log_root, "geotag_process.json")
    try:
        geotag_data = load_json(geotag_process_json_path)
        return geotag_data
    except:
        if verbose:
            print(
                "Warning, geotag data not read for image "
                + image
                + ", therefore it will not be included in the sequence processing."
            )
        return None


def format_orientation(orientation):
    """
    Convert orientation from clockwise degrees to exif tag

    # see http://sylvana.net/jpegcrop/exif_orientation.html
    """
    mapping = {
        0: 1,
        90: 8,
        180: 3,
        270: 6,
    }
    if orientation not in mapping:
        raise ValueError("Orientation value has to be 0, 90, 180, or 270")

    return mapping[orientation]


def load_json(file_path: str):
    try:
        with open(file_path, "rb") as f:
            return json.load(f)
    except:
        return {}


def save_json(data: Dict[str, Any], file_path: str) -> None:
    try:
        buf = json.dumps(data, indent=4)
    except Exception:
        raise RuntimeError(f"Error JSON serializing {data}")
    with open(file_path, "w") as f:
        f.write(buf)


def update_json(data, file_path, process):
    original_data = load_json(file_path)
    original_data[process] = data
    save_json(original_data, file_path)


def get_process_file_list(
    import_path: str,
    process: str,
    rerun: bool = False,
    skip_subfolders: bool = False,
) -> List[str]:
    files = uploader.iterate_files(import_path, not skip_subfolders)
    sorted_files = sorted(
        file
        for file in files
        if uploader.is_image_file(file) and preform_process(file, process, rerun)
    )
    return sorted_files


def get_process_status_file_list(
    import_path: str,
    process: str,
    status: str,
    skip_subfolders: bool = False,
) -> List[str]:
    files = uploader.iterate_files(import_path, not skip_subfolders)
    return sorted(
        file
        for file in files
        if uploader.is_image_file(file) and process_status(file, process, status)
    )


def process_status(file_path: str, process: str, status: str) -> bool:
    log_root = uploader.log_rootpath(file_path)
    status_file = os.path.join(log_root, process + "_" + status)
    return os.path.isfile(status_file)


def get_duplicate_file_list(
    import_path: str, skip_subfolders: bool = False
) -> List[str]:
    files = uploader.iterate_files(import_path, not skip_subfolders)
    return sorted(
        file for file in files if uploader.is_image_file(file) and is_duplicate(file)
    )


def is_duplicate(file_path: str) -> bool:
    log_root = uploader.log_rootpath(file_path)
    duplicate_flag_path = os.path.join(log_root, "duplicate")
    return os.path.isfile(duplicate_flag_path)


def preform_process(file_path: str, process: str, rerun: bool = False) -> bool:
    log_root = uploader.log_rootpath(file_path)
    process_succes = os.path.join(log_root, process + "_success")
    upload_succes = os.path.join(log_root, "upload_success")
    preform = not os.path.isfile(upload_succes) and (
        not os.path.isfile(process_succes) or rerun
    )
    return preform


def processed_images_rootpath(filepath: str) -> str:
    return os.path.join(
        os.path.dirname(filepath),
        ".mapillary",
        "processed_images",
        os.path.basename(filepath),
    )


def video_upload(video_file, import_path, verbose=False):
    import_paths = video_import_paths(video_file)
    if not os.path.isdir(import_path):
        os.makedirs(import_path)
    if import_path not in import_paths:
        import_paths.append(import_path)
    else:
        print(
            f"Warning, {video_file} has already been sampled into {import_path}, please make sure all the previously sampled frames are deleted, otherwise the alignment might be incorrect"
        )
    for video_import_path in import_paths:
        if os.path.isdir(video_import_path):
            if len(uploader.get_success_upload_file_list(video_import_path)):
                if verbose:
                    print("no")
                return 1
    return 0


def create_and_log_video_process(video_file, import_path):
    log_root = uploader.log_rootpath(video_file)
    if not os.path.isdir(log_root):
        os.makedirs(log_root)
    # set the log flags for process
    log_process = os.path.join(log_root, "video_process.json")
    import_paths = video_import_paths(video_file)
    if import_path in import_paths:
        return
    import_paths.append(import_path)
    video_process = load_json(log_process)
    video_process.update({"sample_paths": import_paths})
    save_json(video_process, log_process)


def video_import_paths(video_file):
    log_root = uploader.log_rootpath(video_file)
    if not os.path.isdir(log_root):
        return []
    log_process = os.path.join(log_root, "video_process.json")
    if not os.path.isfile(log_process):
        return []
    video_process = load_json(log_process)
    if "sample_paths" in video_process:
        return video_process["sample_paths"]
    return []


def create_and_log_process_in_list(
    process_file_list: List[str],
    process: str,
    status: str,
    verbose: bool = False,
    mapillary_description: Optional[Dict[str, str]] = None,
) -> None:
    if mapillary_description is None:
        mapillary_description = {}
    for image in tqdm(process_file_list, desc="Logging"):
        create_and_log_process(image, process, status, mapillary_description, verbose)


def create_and_log_process(
    image: str,
    process: str,
    status: str,
    mapillary_description: Optional[Any] = None,
    verbose: bool = False,
) -> None:
    if mapillary_description is None:
        mapillary_description = {}

    # set log path
    log_root = uploader.log_rootpath(image)
    # make all the dirs if not there
    if not os.path.isdir(log_root):
        os.makedirs(log_root)

    # set the log flags for process
    log_process = os.path.join(log_root, process)
    log_process_succes = f"{log_process}_success"
    log_process_failed = f"{log_process}_failed"
    log_MAPJson = os.path.join(log_root, process + ".json")

    if not mapillary_description:
        status = "failed"

    if status == "success":
        suffix = str(time.strftime("%Y_%m_%d_%H_%M_%S", time.gmtime()))
        save_json(mapillary_description, log_MAPJson)
        open(log_process_succes, "w").close()
        open(f"{log_process_succes}_{suffix}", "w").close()
        # if there is a failed log from before, remove it
        if os.path.isfile(log_process_failed):
            os.remove(log_process_failed)
    else:
        open(log_process_failed, "w").close()
        suffix = str(time.strftime("%Y_%m_%d_%H_%M_%S", time.gmtime()))
        open(f"{log_process_failed}_{suffix}", "w").close()
        # if there is a success log from before, remove it
        if os.path.isfile(log_process_succes):
            os.remove(log_process_succes)
        # if there is meta data from before, remove it
        if os.path.isfile(log_MAPJson):
            if verbose:
                print(
                    f"Warning, {process} in this run has failed, previously generated properties will be removed."
                )
            os.remove(log_MAPJson)

    decoded_image = force_decode(image)

    ipc.send(
        process,
        {
            "image": decoded_image,
            "status": status,
            "description": mapillary_description,
        },
    )


def load_geotag_points(
    process_file_list: List[str], verbose: bool = False
) -> Tuple[List[str], List[datetime.datetime], List[float], List[float], List[float]]:
    file_list = []
    capture_times = []
    lats = []
    lons = []
    directions = []

    for image in tqdm(process_file_list, desc="Loading geotag points"):
        log_root = uploader.log_rootpath(image)
        geotag_data = get_geotag_data(log_root, image, verbose)
        if not geotag_data:
            create_and_log_process(image, "sequence_process", "failed", verbose=verbose)
            continue

        # assume all data needed available from this point on
        file_list.append(image)
        capture_times.append(
            datetime.datetime.strptime(
                geotag_data["MAPCaptureTime"], "%Y_%m_%d_%H_%M_%S_%f"
            )
        )
        lats.append(geotag_data["MAPLatitude"])
        lons.append(geotag_data["MAPLongitude"])
        directions.append(
            geotag_data["MAPCompassHeading"]["TrueHeading"]
        ) if "MAPCompassHeading" in geotag_data else directions.append(0.0)

        # remove previously created duplicate flags
        duplicate_flag_path = os.path.join(log_root, "duplicate")
        if os.path.isfile(duplicate_flag_path):
            os.remove(duplicate_flag_path)

    return file_list, capture_times, lats, lons, directions


def split_sequences(
    capture_times: List[datetime.datetime],
    lats: List[float],
    lons: List[float],
    file_list: List[str],
    directions: List[float],
    cutoff_time: float,
    cutoff_distance: float,
    verbose: bool = False,
) -> List[Dict]:
    sequences: List[Dict] = []
    # sort based on time
    sort_by_time = list(zip(capture_times, file_list, lats, lons, directions))
    sort_by_time.sort()
    capture_times, file_list, lats, lons, directions = [
        list(x) for x in zip(*sort_by_time)
    ]
    latlons = list(zip(lats, lons))

    # initialize first sequence
    sequence_index = 0
    sequences.append(
        {
            "file_list": [file_list[0]],
            "directions": [directions[0]],
            "latlons": [latlons[0]],
            "capture_times": [capture_times[0]],
        }
    )

    if len(file_list) >= 1:
        # diff in capture time
        capture_deltas = [t2 - t1 for t1, t2 in zip(capture_times, capture_times[1:])]

        # distance between consecutive images
        distances = [gps_distance(ll1, ll2) for ll1, ll2 in zip(latlons, latlons[1:])]

        # if cutoff time is given use that, else assume cutoff is
        # 1.5x median time delta
        if cutoff_time is None:
            if verbose:
                print(
                    "Warning, sequence cut-off time is None and will therefore be derived based on the median time delta between the consecutive images."
                )
            median = sorted(capture_deltas)[len(capture_deltas) // 2]
            if type(median) is not int:
                median = median.total_seconds()
            cutoff_time = 1.5 * median
        else:
            cutoff_time = float(cutoff_time)
        cut = 0
        for i, filepath in enumerate(file_list[1:]):
            cut_time = capture_deltas[i].total_seconds() > cutoff_time
            cut_distance = distances[i] > cutoff_distance
            if cut_time or cut_distance:
                cut += 1
                # delta too big, start new sequence
                sequence_index += 1
                sequences.append(
                    {
                        "file_list": [filepath],
                        "directions": [directions[1:][i]],
                        "latlons": [latlons[1:][i]],
                        "capture_times": [capture_times[1:][i]],
                    }
                )
                if verbose:
                    if cut_distance:
                        print(
                            f"Cut {cut}: Delta in distance {distances[i]} meters is bigger than cutoff_distance {cutoff_distance} meters at {file_list[i + 1]}"
                        )
                    elif cut_time:
                        print(
                            f"Cut {cut}: Delta in time {capture_deltas[i].total_seconds()} seconds is bigger then cutoff_time {cutoff_time} seconds at {file_list[i + 1]}"
                        )
            else:
                # delta not too big, continue with current
                # group
                sequences[sequence_index]["file_list"].append(filepath)
                sequences[sequence_index]["directions"].append(directions[1:][i])
                sequences[sequence_index]["latlons"].append(latlons[1:][i])
                sequences[sequence_index]["capture_times"].append(capture_times[1:][i])
    return sequences


def interpolate_timestamp(
    capture_times: List[datetime.datetime],
) -> List[datetime.datetime]:
    """
    Interpolate time stamps in case of identical timestamps
    """

    if len(capture_times) < 2:
        return capture_times

    # trace identical timestamps (always assume capture_times is sorted)
    time_dict: OrderedDict[datetime.datetime, Dict] = OrderedDict()
    for i, t in enumerate(capture_times):
        if t not in time_dict:
            time_dict[t] = {"count": 0, "pointer": 0}

            if 0 < i:
                interval = (t - capture_times[i - 1]).total_seconds()
                time_dict[capture_times[i - 1]]["interval"] = interval

        time_dict[t]["count"] += 1

    keys = list(time_dict.keys())
    if len(keys) >= 2:
        # set time interval as the last available time interval
        time_dict[keys[-1]]["interval"] = time_dict[keys[-2]]["interval"]
    else:
        # set time interval assuming capture interval is 1 second
        time_dict[keys[0]]["interval"] = time_dict[keys[0]]["count"] * 1.0

    timestamps = []

    # interpolate timestamps
    for t in capture_times:
        d = time_dict[t]
        s = datetime.timedelta(seconds=d["pointer"] * d["interval"] / float(d["count"]))
        updated_time = t + s
        time_dict[t]["pointer"] += 1
        timestamps.append(updated_time)

    return timestamps


def get_images_geotags(process_file_list):
    geotags = []
    missing_geotags = []
    for image in tqdm(sorted(process_file_list), desc="Reading gps data"):
        exif = ExifRead(image)
        timestamp = exif.extract_capture_time()
        lon, lat = exif.extract_lon_lat()
        altitude = exif.extract_altitude()
        if timestamp and lon and lat:
            geotags.append((timestamp, lat, lon, altitude))
            continue
        if timestamp and (not lon or not lat):
            missing_geotags.append((image, timestamp))
        else:
            print_error(f"Error image {image} does not have captured time.")
    return geotags, missing_geotags
