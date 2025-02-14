## Mapillary Tools

Mapillary Tools is a library for processing and uploading images to [Mapillary](https://www.mapillary.com/).

<!--ts-->

* [Quickstart](#quickstart)
* [Requirements](#requirements)
* [Installation](#installation)
* [Video Support](#video-support)
* [Usage](#usage)
* [Advanced Usage](#advanced-usage)
* [Command Specifications](#command-specifications)
* [Camera Specific](#camera-specific)
* [Troubleshooting](#troubleshooting)
* [Development](#development)

<!--te-->

## Quickstart

Download the latest `mapillary_tools` binaries for your platform here: https://github.com/mapillary/mapillary_tools/releases/tag/v0.7.3

See [more installation instructions](#installation) below.

Upload imagery:

```bash
./mapillary_tools process_and_upload --import_path "path/to/images" --user_name "mapillary_username"
```

## Requirements

### User Authentication

To upload images to Mapillary, an account is required and can be created [here](https://www.mapillary.com/signup). When
using the tools for the first time, user authentication is required. You will be prompted to enter your account
credentials. Only Mapillary account credentials (email and password) are valid for authentication
in `mapillary_tools`. Other Mapillary login options (Facebook, OpenStreetMap, Google+, or ArcGIS) are not supported
with `mapillary_tools`.

### Metadata

To upload images to Mapillary, image `GPS` and `capture time` are minimally required. More
information [here](https://help.mapillary.com/hc/en-us/articles/115001717829-Geotagging-images).

## Installation

### Installing via Pip

Python (3.6 and above) and git are required:

```bash
python3 -m pip install --upgrade git+https://github.com/mapillary/mapillary_tools
```

If you see "Permission Denied" error, try run the command above with `sudo`, or install it in your local [virtualenv](#development) (recommended).

### Installing on Android Devices

A command line program such as Termux is required. Installation can be done without root privileges.  The following commands will install Python 3, pip3, git, and all required libraries for mapillary_tools on Termux:

```bash
pkg install python git build-essential libgeos openssl libjpeg-turbo
python3 -m pip install --upgrade pip wheel
python3 -m pip install --upgrade git+https://github.com/mapillary/mapillary_tools
```

Termux must access the device's internal storage to process and upload images. To do this, use the following command:

```bash
termux-setup-storage
```

Finally, on devices running Android 11, using a command line program, mapillary_tools will process images very slowly if they are in shared internal storage during processing. It is advisable to first move images to the command line program’s native directory before running mapillary_tools.
For an example using Termux, if imagery is stored in the folder “Internal storage/DCIM/mapillaryimages" the following command will move that folder from shared storage to Termux:

```bash
mv -v storage/dcim/mapillaryimages mapillaryimages
```

## Video Support

To sample images from videos, you will also need to install `ffmpeg`.

### Windows

To install `ffmpeg` on Windows, follow
these [instructions](http://adaptivesamples.com/how-to-install-ffmpeg-on-windows/).

### macOS

To install `ffmpeg` on macOS use [Homebrew](https://brew.sh). Once you have Homebrew installed, you can install `ffmpeg`
by running:

```bash
brew install ffmpeg
```

### Ubuntu

To install `ffmpeg` on Ubuntu:

```bash
sudo apt install ffmpeg
```

## Usage

All commands are executed with `mapillary_tools`.

### Available commands

To see the available commands, use the following in the command line (for Windows, adjust the command according the
instructions for execution):

```bash
mapillary_tools -h
```

Executable `mapillary_tools` takes the following arguments:

`-h, --help`: Show help and exit

`--advanced`: Use the tools under an advanced level, with additional arguments and commands available

-----

`command`: Use one of the available commands:

- `process`: Process the images including for instance, geotagging and sequence arrangement
- `upload`: Upload images to Mapillary
- `process_and_upload`: A bundled command for `process` and `upload`

-----

See the command specific help for required and optional arguments:

- Show help for `process` command:

```bash
mapillary_tools process -h
```

-----

- Show advanced help for `process` command:

```bash
mapillary_tools process -h --advanced
```

### Examples

For Windows, adjust the commands according the instructions for execution.

#### Process Images

The command below processes all images in the directory and its sub-directories. It will update the images with
Mapillary-specific metadata in the image EXIF for the user with user name `mapillary_user`. It requires that each image
in the directory contains `capture time` and `GPS`. By default, only the Image Description EXIF tag is overwritten and
duplicate images are flagged to be excluded from upload using default thresholds for duplicate distance 0.1 m and
duplicate angle 5°.

```bash
mapillary_tools process --import_path "path/to/images" --user_name "mapillary_username"
```

#### Upload Images

The command below uploads all images in a directory and its sub-directories. It requires Mapillary-specific metadata in
the image EXIF. It works for images that are captured with Mapillary iOS or Android apps or processed with the `process`
command.

 ```bash
mapillary_tools upload --import_path "path/to/images"
```

#### Process and Upload Images

The command below runs `process` and `upload` consecutively for a directory.

```bash
mapillary_tools process_and_upload --import_path "path/to/images" --user_name "mapillary_username"
```

## Advanced Usage

Available commands for advanced usage:

- Video Specific Commands:
    - sample_video
    - video_process
    - video_process_and_upload
- Process Unit Commands:
    - extract_user_data
    - extract_import_meta_data
    - extract_geotag_data
    - extract_sequence_data
    - extract_upload_params
    - exif_insert
- Other Commands:
    - process_csv
    - interpolate
    - authenticate
    - post_process

### Geotag and Upload

- Run process and upload consecutively, while process is reading geotag data from a gpx track. It requires
  that `capture time` information is embedded in the image EXIF. By default geotag data is stored only in the mapillary
  image description, in the EXIF Image Description tag. If you would like the rest of the tags to be overwritten as
  well, for example to be able to place images on the map for testing purposes, you should pass an additional
  argument `--overwrite_all_EXIF_tags` to overwrite all EXIF tags, or in case you only want to overwrite a specific tag,
  like for example the GPS tag, pass argument `--overwrite_EXIF_gps_tag`.

 ```bash
mapillary_tools process --advanced --import_path "path/to/images" \
    --user_name "mapillary_username" \
    --geotag_source "gpx" \
    --geotag_source_path "path/to/gpx_file"

mapillary_tools upload --import_path "path/to/images"
```

or

 ```bash
mapillary_tools process_and_upload --advanced --import_path "path/to/images" \
    --user_name "mapillary_username" \
    --geotag_source "gpx" \
    --geotag_source_path "path/to/gpx_file"
```

### Keep original images intact and Upload

- To prevent data loss or control versions, the original images can be left intact by specifying the
  flag `--keep_original`. This will result in the edited image being saved in a copy of the original image, instead of
  the original image itself. Copies are saved in `{$import_path/$image_path/}.mapillary/process_images}` and are deleted
  at the start of every processing run.

```bash
mapillary_tools process --advanced --import_path "path/to/images" \
    --user_name "mapillary_username" \
    --keep_original

mapillary_tools upload --import_path "path/to/images"
```

or

 ```bash
mapillary_tools process_and_upload --advanced --import_path "path/to/images" \
    --user_name "mapillary_username" \
    --keep_original
```

### Derive image direction and Upload

- Derive image direction (image heading or camera angle) based on image latitude and longitude. If images are missing
  direction, the direction is derived automatically, if direction is present, it will be derived and overwritten only if
  the flag `--interpolate directions` is specified.

 ```bash
mapillary_tools process --advanced --import_path "path/to/images" \
    --user_name "mapillary_username" \
    --interpolate_directions

mapillary_tools upload --import_path "path/to/images"
```

or

 ```bash
mapillary_tools process_and_upload --advanced --import_path "path/to/images" \
    --user_name "mapillary_username" \
    --interpolate_directions
```

### Video Sampling and Upload

- Sample the video(s) located in `path/to/videos` into the directory `path/to/images`, at a sample interval of 0.5
  seconds and tag the sampled images with `capture time`. Note that the video frames will always be sampled into sub
  directory `.mapillary/sampled_video_frames/"video_import_path"`, whether import path is specified or not. In
  case `import_path` is specified the final path for the sampled video frames will
  be `"import path"/.mapillary/sampled_video_frames/"video_import_path"` and in case `import_path` is not specified, the
  final path for the sampled video frames will be `path/to/.mapillary/sampled_video_frames/"video_import_path"`.

 ```bash
mapillary_tools sample_video --import_path "path/to/images" \
    --video_import_path "path/to/videos" \
    --video_sample_interval 0.5 --advanced 
```

- Sample the video(s) located in `path/to/videos`, at a sample interval of 2 seconds (default value) and tag the
  resulting images with `capture time`. And then process and upload the resulting images for
  user `username_at_mapillary`, specifying a gpx track to be the source of geotag data. Additionally pass
  the `--overwrite_all_EXIF_tags` so the extracted frames have all the tags set beside the Image Description tag.

```bash
mapillary_tools sample_video --video_import_path "path/to/videos" --advanced

mapillary_tools process --advanced --import_path "path/to/.mapillary/sampled_video_frames/video_import_path" \
    --user_name "mapillary_username" \
    --geotag_source "gpx" \
    --geotag_source_path "path/to/gpx_file" \
    --overwrite_all_EXIF_tags

mapillary_tools upload --import_path "path/to/.mapillary/sampled_video_frames/video_import_path"
```

or

```bash
mapillary_tools video_process_and_upload --video_import_path "path/to/videos" \
    --user_name "mapillary_username" \
    --advanced --geotag_source "gpx" \
    --geotag_source_path "path/to/gpx_file" \
    --overwrite_all_EXIF_tags
```

### Process csv

- Insert image capture time and gps data from a csv file, based on filename:

```bash
mapillary_tools process_csv --import_path "path/to/images" \
    --csv_path "path/to/csv_file" \
    --filename_column 1 \
    --timestamp_column 4 \
    --latitude_column 2 \
    --longitude_column 3 \
    --advanced
```

- Insert image capture time and meta data from a csv file based on the order of image file names (in case filename
  column is missing):

```bash
mapillary_tools process_csv --import_path "path/to/images" \
    --csv_path "path/to/csv_file" \
    --timestamp_column 1 \
    --meta_columns "6,7" \
    --meta_names "random_name1,random_name2" \
    --meta_types "double,string" \
    --advanced
```

## Command Specifications

### `process`

The `process` command will format the required and optional meta data into a Mapillary image description and insert it
in the image EXIF Image Description tag. Images are required to contain image capture time, latitude, longitude and
camera direction in the image EXIF. Under advanced usage, additional functionalities are available, for example latitude
and longitude can be read from a gpx track file or a GoPro video, camera direction can be derived based on latitude and
longitude, duplicates can be kept instead of excluded from the upload etc. See the command specific help for required
and optional arguments, add `--advanced` to see additional advanced optional arguments.

#### Examples

- process all images for user `mapillary_user`, in the directory `path/to/images` and its sub-directories:

```bash
mapillary_tools process --import_path "path/to/images" \
    --user_name "mapillary_username"
```

- process all images for user `mapillary_user`, in the directory `path/to/images`, skipping the images in its
  sub-directories, rerunning process for all images that were not already uploaded and printing out extra warnings or
  errors.

```bash
mapillary_tools process --import_path "path/to/images" \
    --user_name "mapillary_username" \
    --verbose \
    --rerun \
    --skip_subfolders
```

#### Advanced Examples

- Process all images for user `mapillary_user`, in the directory `path/to/images` and its sub-directories, reading
  geotag data from a gpx track stored in file `path/to/gpx_file`, specifying an offset of 2 seconds between the camera
  and gps device, ie, camera is 2 seconds ahead of the gps device and specifying to keep duplicates to be uploaded
  instead of flagging images as duplicates in case they are apart by equal or less then the default 0.1 m and differ by
  the camera angle by equal or less than the default 5°. Additionally pass the `--overwrite_EXIF_gps_tag` to overwrite
  values with the values obtained from the gpx track.

```bash
mapillary_tools process --import_path "path/to/images" \
    --user_name "mapillary_username" \
    --advanced \
    --geotag_source "gpx" \
    --geotag_source_path "path/to/gpx_file" \
    --offset_time 2 \
    --keep_duplicates \
    --overwrite_EXIF_gps_tag
```

- Process all images for user `mapillary_user`, in the directory `path/to/images` and its sub-directories, specifying
  the import to be private imagery belonging to an organization with organization username `mapillary_organization`. You
  can find the organization username in your dashboard.

```bash
mapillary_tools process --import_path "path/to/images" \
    --user_name "mapillary_username" \
    --advanced \
    --private \
    --organization_username "mapillary_organization"
```

- Process all images for user `mapillary_user`, in the directory `path/to/images` and its sub-directories, specifying an
  angle offset of 90° for the camera direction and splitting images into sequences of images apart by less than 100
  meters according to image `GPS` and less than 120 seconds according to image `capture time`. Additionally pass
  the `--overwrite_EXIF_direction_tag` to overwrite values with the additional specified offset.

```bash
mapillary_tools process --import_path "path/to/images" \
    --user_name "mapillary_username" \
    --advanced \
    --offset_angle 90 \
    --cutoff_distance 100 \
    --cutoff_time 120 \
    --overwrite_EXIF_direction_tag
```

### `upload`

Images that have been successfully processed or were taken with the Mapillary app will contain the required Mapillary
image description embedded in the image EXIF and can be uploaded with the `upload` command.

The `upload` command will collect all the images in the import path, while checking for duplicate flags, processing and
uploading logs. If image is flagged as duplicate, was logged with failed process or logged as successfully uploaded, it
will not be added to the upload list.

By default, 5 threads upload in parallel and the script retries 50 times upon encountering a failure. These can be
customized by specifying additional arguments `--number_threads` and `--max_attempts` under `--advanced` usage or with
environment variables in the command line:

    NUMBER_THREADS=10
    MAX_ATTEMPTS=100

#### Examples

- upload all images in the directory `path/to/images` and its sub directories:

```bash
mapillary_tools upload --import_path "path/to/images"
```

- upload all images in the directory `path/to/images`, while skipping its sub directories and specifying to upload with
  10 threads and 10 maximum attempts:

```bash
mapillary_tools upload --import_path "path/to/images" \
    --skip_subfolders \
    --number_threads 10 \
    --max_attempts 10 \
    --advanced
```

### `process_and_upload`

`process_and_upload` command will run `process` and `upload` commands consecutively with combined required and optional
arguments.

#### Examples

- process and upload all the images in directory `path/to/images` and its sub-directories for user `mapillary_user`.

```bash
mapillary_tools process_and_upload --import_path "path/to/images" \
    --user_name "mapillary_username"
```

#### Advanced Examples

- Process and upload all the images in directory `path/to/images` and its sub-directories for user `mapillary_user`,
  while specifying duplicate distance and angle threshold so that duplicate images are consecutive images that are less
  than 0.5 meter apart according to image `GPS` and have less than 1° camera angle difference according to image
  direction.

```bash
mapillary_tools process_and_upload --import_path "path/to/images" \
    --user_name "mapillary_username" \
    --verbose \
    --rerun \
    --duplicate_distance 0.5 \
    --duplicate_angle 1 \
    --advanced
```

### `sample_video`

`sample_video` command will sample a video into images and insert `capture time` to the image EXIF. Capture time is
calculated based on the `video start time` and sampling interval. Video start time can either be extracted from the
video metadata or passed as an argument `--video_start_time` (milliseconds since UNIX epoch).

#### Examples

- Sample the video(s) located in `path/to/videos` at the default sampling rate 2 seconds, ie 1 video frame every 2
  seconds. Video frames will be sampled into a sub directory `.mapillary/sampled_video_frames/video_import_path` at the
  location of the video.

```bash
mapillary_tools sample_video --video_import_path "path/to/videos" --advanced
```

- Sample the video(s) located in `path/to/videos` to directory `path/to/images` at a sampling rate 0.5 seconds, ie two
  video frames every second and specifying the video start time to be `156893940910` (milliseconds since UNIX epoch).

```bash
mapillary_tools sample_video --import_path "path/to/images" \
    --video_import_path "path/to/videos" \
    --video_sample_interval 0.5 \
    --video_start_time 156893940910 \
    --advanced
```

### `video_process`

`video_process` command will run `video_sample` and `process` commands consecutively with combined required and optional
arguments.

#### Examples

- In case video start capture time could not be extracted or specified, images should be tagged with `capture time` from
  the external geotag source, by passing the argument `--use_gps_start_time`. To make sure the external source and
  images are aligned ok, an offset in seconds can be specified.

```bash
mapillary_tools video_process --import_path "path/to/images" \
    --video_import_path "path/to/videos" \
    --user_name "mapillary_username" --advanced \
    --geotag_source "gpx" \
    --geotag_source_path "path/to/gpx" \
    --use_gps_start_time \
    --offset_time 2
```

### `video_process_and_upload`

`video_process_and_upload` command will run `video_sample`, `process` and `upload` commands consecutively with combined
required and optional arguments.

#### Examples

- Sample the video(s) located in `path/to/videos` to directory `path/to/images` at the default sampling rate 1 second,
  ie one video frame every second. Process and upload resulting video frames for user `mapillary_user`, reading geotag
  data from a gpx track stored in `path/to/gpx_file` video, assuming video start time can be extracted from the video
  file and deriving camera direction based on `GPS`.

```bash
mapillary_tools video_process_and_upload --import_path "path/to/images" \
    --video_import_path "path/to/videos" \
    --user_name "mapillary_username" \
    --advanced \
    --geotag_source "gpx" \
    --geotag_source_path "path/to/gpx_file" \
    --video_sample_interval 1 \
    --interpolate_directions
```

### Process Unit Commands

Process unit commands are commands executed by the `process` command. Usage of process unit commands requires the
flag `--advanced` to be passed and might require some experience with mapillary_tools.

#### `extract_user_data`

`extract_user_data` will process user specific properties and initialize authentication in case of first import.
Credentials are then stored in a global config file and read from there in further imports.

#### `extract_import_meta_data`

`extract_import_meta_data` will process import specific meta data which is not required, but can be very useful. Import
meta data is read from EXIF and/or can be passed through additional arguments.

#### `extract_geotag_data`

`extract_geotag_data` will process image capture date/time, latitude, longitude and camera angle. By default geotag data
is read from image EXIF. Under advanced usage, a different source of latitude, longitude and camera direction can be
specified. Geotagging can be adjusted for better quality, by specifying an offset angle for the camera direction or an
offset time between the camera and gps device.

#### `extract_sequence_data`

`extract_sequence_data` will process the entire set of images located in the import path and create sequences, initially
based on the file system structure, then based on image capture time and location and in the end splitting sequences
longer than 500 images. By default, duplicates are flagged to be excluded from upload, using the default duplicate
thresholds for distance 0.1 m and angle 5°. Optionally, duplicates can be kept and camera directions can be derived
based on latitude and longitude.

#### `extract_upload_params`

`extract_upload_params` will process user specific upload parameters, required to safely upload images to Mapillary.

#### `exif_insert`

`exif_insert` will take all the meta data read and processed in the other processing unit commands and insert it in the
image EXIF tag Image Description only, unless additional arguments are passed in order to overwrite the rest of EXIF
tags as well.

### Other Commands

#### `authenticate`

`authenticate` will update the user credentials stored in `~/.config/mapillary/config`. Mapillary acount `user_name`
, `user_email` and `user_password` are required and can either be passed as arguments to the command or left unspecified
and entered upon prompt.

#### `interpolate`

`interpolate` will interpolate identical timestamps in a csv file or stored in image EXIF or will interpolate missing
gps data in a set of otherwise geotagged images.

#### `process_csv`

`process_csv` will parse the specified csv file and insert data in the image EXIF.

#### `post_process`

`post_process` provides functionalities to help summarize and organize the results of the `process` and/or `upload`
commands.

## Camera specific

### BlackVue
#### Local sampling

- Sample one or more Blackvue videos in directory `path/to/videos` into import path `path/to/images` at a sampling rate
  0.2 seconds, ie 5 frames every second and process resulting video frames for user `mapillary_user`, reading geotag
  data from the Blackvue videos in `path/to/videos` and specifying camera make and model, specifying to derive camera
  direction based on `GPS` and use the `GPS` start time. Note that video frames will be sampled
  into `path/to/images/.mapillary/sampled_video_frames/"video_import_path"`. Video frames will be geotagged after all
  the videos in the specified `video_import_path` have been sampled. In case video frames geotagging requires `rerun`,
  there is no need to rerun the entire `video_process` command, in case video frame extraction was successful, rerunning
  only the `process` command for the given `import_path` is sufficient. We encourage users to check and specify camera
  make and model, since it helps with camera calibration and improves 3D reconstruction. If you want to check the video
  frame placement on the map before uploading, specify `--overwrite_EXIF_gps_tag`.

```bash
mapillary_tools video_process --import_path "path/to/images" \
    --video_import_path "path/to/videos" \
    --user_name "mapillary_username" \
    --advanced \
    --geotag_source "blackvue_videos" \
    --geotag_source_path "path/to/videos" \
    --use_gps_start_time \
    --interpolate_directions \
    --video_sample_interval 0.2 \
    --device_make "Blackvue" \
    --device_model "DR900S-2CH" \
    --overwrite_EXIF_gps_tag
```

### GoPro

- Sample one or more GoPro videos in directory `path/to/videos` into import path `path/to/images` at a sampling rate 0.5
  seconds, ie 2 frames every second and process resulting video frames for user `mapillary_user`, reading geotag data
  from the GoPro videos in `path/to/videos` and specifying to derive camera direction based on `GPS`. Note that video
  frames will be sampled into `path/to/images/.mapillary/sampled_video_frames/"video_import_path"`. Video frames will be
  geotagged after all the videos in the specified `video_import_path` have been sampled. In case video frames geotagging
  requires `rerun`, there is no need to rerun the entire `video_process` command, in case video frame extraction was
  successful, rerunning only the `process` command for the given `import_path` is sufficient. If you want to check the
  video frame placement on the map before uploading, specify `--overwrite_EXIF_gps_tag`.

```bash
mapillary_tools video_process --import_path "path/to/images" \
    --video_import_path "path/to/videos" \
    --user_name "mapillary_username" \
    --advanced \
    --geotag_source "gopro_videos" \
    --geotag_source_path "path/to/videos" \
    --interpolate_directions \
    --video_sample_interval 0.5 \
    --overwrite_EXIF_gps_tag
```

## Troubleshooting

In case of any issues with the installation and usage of `mapillary_tools`, check this section in case it has already
been addressed, otherwise, open an issue on Github.

### General

- In case of any issues, it is always safe to try and rerun the failing command while specifying `--verbose` to see more
  information printed out. Uploaded images should not get uploaded more than once and should not be processed after
  uploading. mapillary_tools should take care of that, if it occurs otherwise, please open an issue on Github.
- Make sure you run the latest version of `mapillary_tools`, which you can check with `mapillary_tools --version`. When
  installing the latest version, don't forget you need to specify `--upgrade`.
- Advanced user are encouraged to explore the processed data and log files in
  the `{image_path}/.mapillary/logs/{image_name}/` to get more insight in the failure.

### Run time issues

- HTTP Errors can occur due to poor network connection or high load on the import pipeline. In most cases the images
  eventually get uploaded regardless. But in some cases HTTP Errors can occur due to authentication issues, which can be
  resolved by either removing the config file with the users credentials, located in `~/.config/mapillary/config` or
  running the `authenticate` command available under advanced usage of `mapillary_tools`.

- Windows users sometimes have issues with the prompt not functioning. This usually results in mapillary_tools just
  hanging without printing anything or creating any logs in `{image_path}/.mapillary/logs/{image_name}`. In such cases
  authentication should be run separately with the `authentication` command, while passing `user_name`, `user_email`
  and `user_password` as command line arguments. This will avoid the prompt and will authenticate the user for all
  further usage of the `process` command.

- Missing required data is often the reason for failed uploads, especially if the processing included parsing external
  data like a gps trace. Images are aligned with a gps trace based on the image capture time and gps time, where the
  default assumption is that both are in UTC. Check the begin and end date of your capture and the begin and end date of
  the gps trace to make sure that the image capture time is in the scope of the gps trace. To correct any offset between
  the two capture times, you can specify `--offset_time "offset time"`. Timezone differences can result in such issues,
  if you know that the image capture time was stored in your current local timezone, while the gps trace is stored in
  UTC, specify `--local_time`. If images do not contain capture time or the capture time is unreliable, while gps time
  is accurate, specify `use_gps_start_time`.

- In cases where the `import_path` is located on an external mount, images can potentially get overwritten, if breaking
  the script with Ctrl+c. To keep the images intact, you can specify `--keep_original` and all the processed data will
  be inserted in a copy of the original image. We are still in progress of improving this step of data import and will
  make sure that no image gets overwritten at any point.

### Upload quality issues

- Some devices do not store the camera direction properly, often storing only 0. Camera direction will get derived based
  on latitide and longitude only if the camera direction is not set or `--interpolate_directions` is specified. Before
  processing and uploading images, make sure that the camera direction is either correct or missing and in case it is
  present but incorrect, you specify `-interpolate_directions`.
- Timestamp interpolation is required in case the latitude and longitude are stored in an external gps trace with a
  higher capture frequency then the image capture frequency which results in identical image capture times.
  Command `interpolate` can be used to interpolate image capture time:

```bash
mapillary_tools interpolate --data "identical_timestamps" --import_path "path/to/images" --advanced 
 ```

- If `process` includes correction of existing EXIF tag values or extraction of missing EXIF tag values from external
  sources and you want to test the placement on the map before uploading the images, make sure you
  pass `--advanced --overwrite_all_EXIF_tags` so that the rest of tags beside Image Description tag will get updated
  with the values obtained during `process`.

## Development

Clone the repository:

```bash
git clone git@github.com:mapillary/mapillary_tools.git
cd mapillary_tools
```

Set up the virtual environment. It is optional but recommended:

```bash
python3 -m venv venv
source venv/bin/activate # For Windows, run: .\venv\Scripts\activate
# verify if the venv is activated
which python3
```

Install dependencies:

```
python3 -m pip install -r requirements.txt
python3 -m pip install -r requirements-dev.txt
```

Run the code from the repository:

```
python3 -m mapillary_tools --version
```

Run tests:

```
pytest tests
```

Run linting:

```
black mapillary_tools tests
```
