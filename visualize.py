#!/usr/bin/env python3

import argparse
import os
import time
import yaml
import numpy as np
from auxiliary.laserscan import *
from auxiliary.laserscanvis import LaserScanVis
from auxiliary.tools import convert_range


def parse_calibration(filename):
  """ read calibration file with given filename

      Returns
      -------
      dict
          Calibration matrices as 4x4 numpy arrays.
  """
  calib = {}

  calib_file = open(filename)
  for line in calib_file:
    key, content = line.strip().split(":")
    values = [float(v) for v in content.strip().split()]

    pose = np.zeros((4, 4))
    pose[0, 0:4] = values[0:4]
    pose[1, 0:4] = values[4:8]
    pose[2, 0:4] = values[8:12]
    pose[3, 3] = 1.0

    calib[key] = pose

  calib_file.close()

  return calib


def parse_poses(filename, calibration):
  """ read poses file with per-scan poses from given filename

      Returns
      -------
      list
          list of poses as 4x4 numpy arrays.
  """
  file = open(filename)

  poses = []

  Tr = calibration["Tr"]
  Tr_inv = np.linalg.inv(Tr)

  pose = np.eye(4)

  i = 0
  for line in file:
    values = [float(v) for v in line.strip().split()]

    cur_pose = np.zeros((4, 4))
    cur_pose[0, 0:4] = values[0:4]
    cur_pose[1, 0:4] = values[4:8]
    cur_pose[2, 0:4] = values[8:12]
    cur_pose[3, 3] = 1.0

    pose = cur_pose
    poses.append(np.matmul(Tr_inv, np.matmul(pose, Tr)))
    i += 1

  return poses

if __name__ == '__main__':
  parser = argparse.ArgumentParser("./lidar_deform.py")
  parser.add_argument(
      '--dataset', '-d',
      type=str,
      required=True,
      help='Dataset to adapt. No Default',
  )
  parser.add_argument(
      '--config', '-c',
      type=str,
      required=False,
      default="config/lidar_transfer.yaml",
      help='Dataset config file. Defaults to %(default)s',
  )
  parser.add_argument(
      '--sequence', '-s',
      type=str,
      default="00",
      required=False,
      help='Sequence to visualize. Defaults to %(default)s',
  )
  parser.add_argument(
      '--predictions', '-p',
      type=str,
      default=None,
      required=False,
      help='Alternate location for labels, to use predictions folder. '
      'Must point to directory containing the predictions in the proper format '
      ' (see readme)'
      'Defaults to %(default)s',
  )
  parser.add_argument(
      '--ignore_semantics', '-i',
      dest='ignore_semantics',
      default=False,
      action='store_true',
      help='Ignore semantics. Visualizes uncolored pointclouds.'
      'Defaults to %(default)s',
  )
  parser.add_argument(
      '--offset', '-o',
      type=int,
      default=0,
      required=False,
      help='Sequence to start. Defaults to %(default)s',
  )
  FLAGS, unparsed = parser.parse_known_args()

  # print summary of what we will do
  print("*" * 80)
  print("INTERFACE:")
  print("Dataset", FLAGS.dataset)
  print("Config", FLAGS.config)
  print("Sequence", FLAGS.sequence)
  print("Predictions", FLAGS.predictions)
  print("ignore_semantics", FLAGS.ignore_semantics)
  print("offset", FLAGS.offset)
  print("*" * 80)

  # open config file
  try:
    print("Opening config file %s" % FLAGS.config)
    CFG = yaml.safe_load(open(FLAGS.config, 'r'))
  except Exception as e:
    print(e)
    print("Error opening yaml file.")
    quit()

  # does sequence folder exist?
  scan_paths = os.path.join(FLAGS.dataset, "sequences",
                            FLAGS.sequence, "velodyne")
  if os.path.isdir(scan_paths):
    print("Sequence folder exists! Using sequence from %s" % scan_paths)
  else:
    print("Sequence folder doesn't exist! Exiting...")
    quit()

  # get pointclouds filenames
  scan_names = [os.path.join(dp, f) for dp, dn, fn in os.walk(
      os.path.expanduser(scan_paths)) for f in fn]
  scan_names.sort()

  # does label folder exist?
  if FLAGS.ignore_semantics is False:
    if FLAGS.predictions is not None:
      label_paths = os.path.join(FLAGS.predictions, "sequences",
                                 FLAGS.sequence, "predictions")
    else:
      label_paths = os.path.join(FLAGS.dataset, "sequences",
                                 FLAGS.sequence, "labels")
    if os.path.isdir(label_paths):
      print("Labels folder exists! Using labels from %s" % label_paths)
    else:
      print("Labels folder doesn't exist! Exiting...")
      quit()

    # get label filenames
    label_names = [os.path.join(dp, f) for dp, dn, fn in os.walk(
        os.path.expanduser(label_paths)) for f in fn]
    label_names.sort()

    # check that there are same amount of labels and scans
    assert(len(label_names) == len(scan_names))

  # read config.yaml of dataset
  try:
    scan_config_path = os.path.join(FLAGS.dataset, "config.yaml")
    print("Opening config file", scan_config_path)
    scan_config = yaml.safe_load(open(scan_config_path, 'r'))
  except Exception as e:
    print(e)
    print("Error opening config.yaml file %s." % scan_config_path)
    quit()

  # read calib.txt of dataset
  try:
    calib_file = os.path.join(FLAGS.dataset, "sequences",
                              FLAGS.sequence, "calib.txt")
    print("Opening calibration file", calib_file)
  except Exception as e:
    print(e)
    print("Error opening poses file.")
    quit()
  calib = parse_calibration(calib_file)

  # read poses.txt of dataset
  try:
    poses_file = os.path.join(FLAGS.dataset, "sequences",
                              FLAGS.sequence, "poses.txt")
    print("Opening poses file", poses_file)
  except Exception as e:
    print(e)
    print("Error opening poses file.")
    quit()
  poses = parse_poses(poses_file, calib)

  # additional parameter
  name = scan_config['name']
  # projection = scan_config['projection']
  fov_up = scan_config['fov_up']
  fov_down = scan_config['fov_down']
  # TODO change to more general description height?
  beams = scan_config['beams']
  angle_res_hor = scan_config['angle_res_hor']
  fov_hor = scan_config['fov_hor']
  try:
    beam_angles = scan_config['beam_angles']
    beam_angles.sort()
  except Exception as e:
    beam_angles = None
    print("No beam angles in scan config: calculate equidistant angles")
  W = int(fov_hor / angle_res_hor)
  ignore_classes = CFG["ignore"]
  moving_classes = CFG["moving"]

  print("*" * 80)
  print("SCANNER:")
  print("Name", name)
  print("Resolution", beams, "x", W)
  print("FOV up", fov_up)
  print("FOV down", fov_down)
  print("Beam angles", beam_angles)
  print("Ignore classes", ignore_classes)
  print("Moving classes", moving_classes)
  print("*" * 80)

  # create a scan
  color_dict = CFG["color_map"]
  nclasses = len(color_dict)

  # create a visualizer
  show_diff = False
  show_mesh = False
  show_range = False
  vis = LaserScanVis([W, W], [beams, beams], show_diff=show_diff,
                     show_range=show_range, show_mesh=show_mesh)
  vis.nframes = len(scan_names)

  if FLAGS.ignore_semantics:
    vis.img_canvas.title = "Range image"
    vis.test_canvas.title = "Label image"
  else:
    vis.img_canvas.title = "Label image"
    vis.test_canvas.title = "Range image"
  vis.grid_view.remove_widget(vis.back_view)

  # print instructions
  print("To navigate:")
  print("\tb: back (previous scan)")
  print("\tn: next (next scan)")
  print("\tq: quit (exit program)")

  idx = FLAGS.offset

  while True:
    t0_elapse = time.time()

    if FLAGS.ignore_semantics is False:
      scan = SemLaserScan(beams, W, nclasses, color_dict)
    else:
      scan = LaserScan(beams, W)

    # open pointcloud
    scan.open_scan(scan_names[idx], fov_up, fov_down)
    if FLAGS.ignore_semantics is False:
      scan.open_label(label_names[idx])
      scan.colorize()
      scan.remove_classes(ignore_classes)
    scan.do_range_projection(fov_up, fov_down, remove=False)
    if FLAGS.ignore_semantics is False:
      scan.do_label_projection()

    # pass to visualizer!
    vis.frame = idx
    vis.set_title()
    vis.set_laserscan(scan)
    if FLAGS.ignore_semantics is False:
      data = convert_range(scan.proj_range)
      vis.test_vis.set_data(data)
      vis.test_vis.update()

    # get user choice
    while True:
      choice = vis.get_action(0.01)
      if choice != "no":
        break
    if choice == "next":
      # take into account that we look further than one scan
      idx = (idx + 1) % (len(scan_names) - 1)
      continue
    if choice == "back":
      idx -= 1
      if idx < 0:
        idx = len(scan_names) - 1
      continue
    elif choice == "quit":
      print()
    break
