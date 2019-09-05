#!/usr/bin/env python3

import vispy
from vispy.scene import visuals, SceneCanvas
import numpy as np
from matplotlib import pyplot as plt
from auxiliary.np_ioueval import iouEval
from auxiliary.tools import get_mpl_colormap, convert_range


class LaserScanVis():
  """Class that creates and handles a visualizer for a pointcloud"""

  def __init__(self, W, H, show_mesh=False, show_diff=False, show_range=False,
               show_remissions=False, show_target=True, show_label=True):
    self.W = W
    self.H = H
    self.point_size = 3
    self.frame = 0
    self.nframes = 0
    self.view_mode = 'label'
    self.show_label = show_label
    self.show_target = show_target
    self.show_mesh = show_mesh
    self.show_remissions = show_remissions
    self.show_diff = show_diff
    self.show_range = show_range
    self.reset()

  def reset(self):
    """ Reset. """
    # last key press (it should have a mutex, but visualization is not
    # safety critical, so let's do things wrong)
    self.action = "no"  # no, next, back, quit are the possibilities

    # 3D canvas
    self.scan_canvas = SceneCanvas(keys='interactive', show=True, title='',
                                   size=(1600, 600), bgcolor='white')
    self.scan_canvas.events.key_press.connect(self.key_press)
    self.grid_view = self.scan_canvas.central_widget.add_grid()
    
    # source laserscan 3D
    self.scan_view = vispy.scene.widgets.ViewBox(
      border_color='white', parent=self.scan_canvas.scene)
    self.scan_vis = visuals.Markers()
    self.scan_view.camera = 'turntable'
    self.scan_view.add(self.scan_vis)
    visuals.XYZAxis(parent=self.scan_view.scene)
    self.grid_view.add_widget(self.scan_view, 0, 0)

    # target laserscan 3D
    if self.show_target is True:
    self.back_view = vispy.scene.widgets.ViewBox(
      border_color='white', parent=self.scan_canvas.scene)
    self.back_vis = visuals.Markers()
    self.back_view.camera = 'turntable'
    self.back_view.camera.link(self.scan_view.camera)
    self.back_view.add(self.back_vis)
    visuals.XYZAxis(parent=self.back_view.scene)
    self.grid_view.add_widget(self.back_view, 0, 1)

    # self.grid_view.padding = 6

    h = 1
    if self.show_range is True:
      h += 1
    if self.show_remissions is True:
      h += 1

    # source canvas 2D
    source_canvas_title = 'Source ' + str(self.H[0]) + 'x' + str(self.W[0])
    self.source_canvas = SceneCanvas(keys='interactive', show=True,
                                     title=source_canvas_title,
                                     size=(self.W[0], h * self.H[0]))
    self.source_canvas.events.key_press.connect(self.key_press)
    self.source_view = self.source_canvas.central_widget.add_grid()
    source_grid_idx = 0

    # Add label image
    if self.show_label:
      self.img_view = vispy.scene.widgets.ViewBox(
          border_color='white', parent=self.source_canvas.scene)
    self.img_vis = visuals.Image(cmap='viridis')
    self.img_view.add(self.img_vis)
      self.source_view.add_widget(self.img_view, source_grid_idx, 0)
      source_grid_idx += 1

    # target canvas 2D
    if self.show_target:
      target_canvas_title = 'Target ' + str(self.H[1]) + 'x' + str(self.W[1])
      self.target_canvas = SceneCanvas(keys='interactive', show=True,
                                       title=target_canvas_title,
                                       size=(self.W[1], h * self.H[1]))
      self.target_canvas.events.key_press.connect(self.key_press)
      self.target_view = self.target_canvas.central_widget.add_grid()
      target_grid_idx = 0

      # Add label image
      if self.show_label:
        self.test_view = vispy.scene.widgets.ViewBox(
            border_color='white', parent=self.target_canvas.scene)
    self.test_vis = visuals.Image(cmap='viridis')
    self.test_view.add(self.test_vis)
        self.target_view.add_widget(self.test_view, target_grid_idx, 0)
        target_grid_idx += 1

    if self.show_range:
      self.range_view_source = vispy.scene.widgets.ViewBox(
          border_color='white', parent=self.source_canvas.scene)
      # self.range_image_source = visuals.Image(cmap='viridis')
      self.range_image_source = visuals.Image()
      self.range_view_source.add(self.range_image_source)
      self.source_view.add_widget(self.range_view_source, source_grid_idx, 0)
      source_grid_idx += 1

      if self.show_target:
      self.range_view_target = vispy.scene.widgets.ViewBox(
            border_color='white', parent=self.target_canvas.scene)
      self.range_image_target = visuals.Image(cmap='viridis')
      self.range_view_target.add(self.range_image_target)
        self.target_view.add_widget(self.range_view_target, target_grid_idx, 0)
        target_grid_idx += 1

    if self.show_remissions:
      self.remissions_view_source = vispy.scene.widgets.ViewBox(
          border_color='white', parent=self.source_canvas.scene)
      # self.remissions_image_source = visuals.Image(cmap='viridis')
      self.remissions_image_source = visuals.Image()
      self.remissions_view_source.add(self.remissions_image_source)
      self.source_view.add_widget(self.remissions_view_source, source_grid_idx, 0)
      source_grid_idx += 1

      if self.show_target:
        self.remissions_view_target = vispy.scene.widgets.ViewBox(
            border_color='white', parent=self.target_canvas.scene)
        self.remissions_image_target = visuals.Image(cmap='viridis')
        self.remissions_view_target.add(self.remissions_image_target)
        self.target_view.add_widget(self.remissions_view_target, target_grid_idx, 0)
        target_grid_idx += 1

    # NEW canvas for showing difference in range and labels
    if self.show_diff:
    self.diff_canvas = SceneCanvas(keys='interactive', show=True,
                                   title='Difference Range Image',
                                     size=(self.W[1], self.H[1] * h))
    self.diff_canvas.events.key_press.connect(self.key_press)
    self.diff_view = self.diff_canvas.central_widget.add_grid()
      grid_idx = 0

      self.diff_view_label = vispy.scene.widgets.ViewBox(
          border_color='white', parent=self.diff_canvas.scene)
      self.diff_image_label = visuals.Image(cmap='viridis')
      self.diff_view_label.add(self.diff_image_label)
      self.diff_view.add_widget(self.diff_view_label, grid_idx, 0)
      grid_idx += 1

      if self.show_range:
    self.diff_view_depth = vispy.scene.widgets.ViewBox(
      border_color='white', parent=self.diff_canvas.scene)
    # self.diff_image_depth = visuals.Image(cmap='viridis')
    self.diff_image_depth = visuals.Image()
    self.diff_view_depth.add(self.diff_image_depth)
        self.diff_view.add_widget(self.diff_view_depth, grid_idx, 0)
        grid_idx += 1

      if self.show_remissions:
        self.diff_view_remissions = vispy.scene.widgets.ViewBox(
      border_color='white', parent=self.diff_canvas.scene)
        # self.diff_image_remissions = visuals.Image(cmap='viridis')
        self.diff_image_remissions = visuals.Image()
        self.diff_view_remissions.add(self.diff_image_remissions)
        self.diff_view.add_widget(self.diff_view_remissions, grid_idx, 0)
        grid_idx += 1

    if self.show_mesh:
      self.mesh_view = vispy.scene.widgets.ViewBox(
          border_color='white', parent=self.scan_canvas.scene)
      self.mesh_vis = visuals.Mesh(shading=None)
      self.mesh_view.camera = 'turntable'
      self.mesh_view.camera.link(self.scan_view.camera)
      self.mesh_view.add(self.mesh_vis)
      visuals.XYZAxis(parent=self.mesh_view.scene)
      self.grid_view.add_widget(self.mesh_view, 0, 2)

  def set_laserscan(self, scan):
    # plot range
    if hasattr(scan, 'label_color'):
      # print(scan.label_color.shape)
      self.scan_vis.set_data(scan.points,
                             face_color=scan.label_color[..., ::-1],
                             edge_color=scan.label_color[..., ::-1],
                             size=self.point_size)
    else:
      power = 16
      range_data = np.copy(scan.unproj_range)
      range_data = range_data**(1 / power)
      # print(range_data.max(), range_data.min())
      viridis_range = ((range_data - range_data.min()) /
                       (range_data.max() - range_data.min()) *
                       255).astype(np.uint8)
      viridis_map = get_mpl_colormap("viridis")
      viridis_colors = viridis_map[viridis_range]
      self.scan_vis.set_data(scan.points,
                             face_color=viridis_colors[..., ::-1],
                             edge_color=viridis_colors[..., ::-1],
                             size=self.point_size)
    self.scan_vis.update()

    # plot range image
    if hasattr(scan, 'proj_color'):
      self.img_vis.set_data(scan.proj_color[..., ::-1])
    else:
      data = convert_range(scan.proj_range)
      self.img_vis.set_data(data)
    self.img_vis.update()

  def set_laserscans(self, scan):
    # plot 3D
    if hasattr(scan.merged, 'label_color'):
      label_color = scan.merged.label_color_image.reshape(-1, 3)
      points = scan.merged.back_points.reshape(-1, 3)
      self.back_vis.set_data(points,
                             face_color=label_color[..., ::-1],
                             edge_color=label_color[..., ::-1],
                             size=self.point_size)
    else:
      power = 16
      range_data = np.copy(scan.get_scan(0).unproj_range)
      # print(range_data.max(), range_data.min())
      range_data = range_data**(1 / power)
      # print(range_data.max(), range_data.min())
      viridis_range = ((range_data - range_data.min()) /
                       (range_data.max() - range_data.min()) *
                       255).astype(np.uint8)
      viridis_map = get_mpl_colormap("viridis")
      viridis_colors = viridis_map[viridis_range]
      self.back_vis.set_data(scan.get_scan(0).points,
                             face_color=viridis_colors[..., ::-1],
                             edge_color=viridis_colors[..., ::-1],
                             size=self.point_size)
    self.back_vis.update()

    # plot label image test
    if hasattr(scan.get_scan(0), 'proj_color'):
      self.test_vis.set_data(scan.merged.proj_color[..., ::-1])
    else:
      # print()
      data = convert_range(scan.get_scan(0).proj_range)
      self.test_vis.set_data(data)
    self.test_vis.update()

  def set_title(self):
    self.scan_canvas.title = 'Frame %d of %d' % (self.frame + 1, self.nframes)

  def set_source_scan(self, scan):
    """ Set single raw scan
    """
    # plot 2D images
    if self.show_label:
      self.img_vis.set_data(scan.proj_color[..., ::-1])
    if self.show_range:
      data = convert_range(scan.proj_range)
      self.range_image_source.set_data(data)
    if self.show_remissions:
      # data = convert_range(scan.proj_remissions)
      data = scan.proj_remissions
      self.remissions_image_source.set_data(data)
    self.img_vis.update()

  def set_data(self, scan_source, scan_target, verts=None, verts_colors=None,
               faces=None, W=None, H=None):
    self.set_title()

    if self.show_target:
      self.set_target_3d(scan_target)

    if self.show_label:
      self.img_vis.set_data(scan_source.proj_color[..., ::-1])
      if self.show_target:
        self.test_vis.set_data(scan_target.proj_color[..., ::-1])

    if self.show_range:
      source_data = scan_source.proj_range
      # print("source", source_data.max(), source_data.min(), source_data[source_data>=0].mean())
      # source_data = self.convert_ranges(scan_source.proj_range)
      self.range_image_source.set_data(source_data)
      self.range_image_source.update()
      if self.show_target:
        target_range = scan_target.proj_range
      # target_data = self.convert_range(target_range)
        # print("target", target_data.max(), target_data.min(), target_data.mean())
      target_data = target_range
      self.range_image_target.set_data(target_data)
      self.range_image_target.update()

    if self.show_remissions:
      source_data = scan_source.proj_remissions
      self.remissions_image_source.set_data(source_data)
      self.remissions_image_source.update()
      if self.show_target:
        target_data = scan_target.proj_remissions
        self.remissions_image_target.set_data(target_data)
        self.remissions_image_target.update()

    if self.show_mesh:
      self.mesh_vis.set_data(vertices=verts,
                             vertex_colors=verts_colors[..., ::-1],
                             faces=faces)
      self.mesh_vis.update()

  def set_diff2(self, label_diff, range_diff, remissions_diff, m_iou, m_acc,
                MSE):
    if self.show_label:
    self.diff_image_label.set_data(label_diff[..., ::-1])
    self.diff_image_label.update()

    if self.show_range:
    data = convert_range(range_diff)
    self.diff_image_depth.set_data(data)
    self.diff_image_depth.set_data(range_diff)
    self.diff_image_depth.update()

    if self.show_remissions:
      self.diff_image_remissions.set_data(remissions_diff)
      self.diff_image_remissions.update()

    self.diff_canvas.title = \
        'IoU %5.2f%%, Acc %5.2f%%, MSE %f' % (m_iou * 100.0, m_acc * 100, MSE)

  def set_diff(self, scan_source, scan_target):
    if not self.show_diff:
      return

    # Label intersection image
    source_label = scan_source.proj_color
    source_label_map = scan_source.get_label_map()

    if scan_target.adaption == 'cp':
      target_label_map = scan_target.merged.get_label_map()
      target_label = scan_target.merged.proj_color
    else:
      target_label = scan_target.proj_color
      target_label_map = scan_target.get_label_map()

    # Mask out no data (= black) in target scan
    black = np.sum(source_label, axis=2) == 0
    black = np.repeat(black[:, :, np.newaxis], 3, axis=2)
    target_label[black] = 0
    black = source_label_map == 0
    target_label_map[black] = 0

    # Ignore empty classes
    unique_values = np.unique(source_label_map)
    empty = np.isin(np.arange(scan_source.nclasses), unique_values,
                    invert=True)
    
    # Evaluate by label
    # eval = iouEval(scan_source.nclasses,
    #                np.arange(scan_source.nclasses)[empty])
    # eval.addBatch(target_label_map, source_label_map)
    # m_iou, iou = eval.getIoU()
    # print("IoU class: ", (iou * 100).astype(int))
    # m_acc = eval.getacc()
    # print("IoU: ", m_iou)
    # print("Acc: ", m_acc)

    label_diff = abs(source_label - target_label)
    self.diff_image_label.set_data(label_diff[..., ::-1])
    self.diff_image_label.update()

    # Range diff image
    source_range = scan_source.proj_range
      target_range = scan_target.proj_range
    # Mask out no data (= black) in target scan
    black = source_range == 0
    # target_range[black] = 0

    # Mask out too far data in target scan
    # too_far = source_range >= 80
    # source_range[too_far] = 0
    # target_range[too_far] = 0

    # print(np.amax(source_range))

    range_diff = (source_range - target_range) ** 2

    data = convert_range(range_diff)
    # self.diff_image_depth.set_data(data)
    self.diff_image_depth.set_data(range_diff)
    self.diff_image_depth.update()

    # temp = np.copy(range_diff)
    # print((range_diff==1).sum())
    # temp[range_diff==1] = 0.0
    # MSE = range_diff.sum() / range_diff.size
    # print("MSE: ", MSE)

    # self.diff_canvas.title = \
    #     'IoU %5.2f%%, Acc %5.2f%%, MSE %f' % (m_iou * 100.0, m_acc * 100, MSE)

  def set_mesh(self, verts, verts_colors, faces):
    if self.show_mesh:
      self.mesh_vis.set_data(vertices=verts,
                             vertex_colors=verts_colors,
                             faces=faces)
      self.mesh_vis.update()

  def set_points(self, points, colors, W, H):
    # plot range
    self.back_vis.set_data(points,
                           face_color=colors[..., ::-1],
                           edge_color=colors[..., ::-1],
                           size=self.point_size)
    self.back_vis.update()

    # plot range image test
    self.test_vis.set_data(colors.reshape(H, W, 3)[..., ::-1])
    self.test_vis.update()


  def set_source_3d(self, scan_source):
    points = scan_source.points

    if self.view_mode == 'label':
      colors = scan_source.label_color
    else:
      if self.view_mode == 'range':
        range_data = np.copy(scan_source.unproj_range.reshape(-1))
        power = 2
        range_data = range_data**(1 / power)
        viridis_range = ((range_data - range_data.min()) /
                         (range_data.max() - range_data.min()) *
                         255).astype(np.uint8)
      elif self.view_mode == 'rem':
        range_data = np.copy(scan_source.remissions.reshape(-1))
        viridis_range = (range_data * 255 ).astype(np.uint8)
      viridis_map = get_mpl_colormap("viridis")
      colors = viridis_map[viridis_range]

    self.scan_vis.set_data(points,
                           face_color=colors[..., ::-1],
                           edge_color=colors[..., ::-1],
                           size=self.point_size)
    self.scan_vis.update()

  def set_target_3d(self, scan_target):
    points = scan_target.back_points

    if self.view_mode == 'label':
      colors = scan_target.label_color
    else:
      if self.view_mode == 'range':
        range_data = np.copy(scan_target.proj_range.reshape(-1))
        power = 2
        range_data = range_data**(1 / power)
        viridis_range = ((range_data - range_data.min()) /
                         (range_data.max() - range_data.min()) *
                         255).astype(np.uint8)
      elif self.view_mode == 'rem':
        range_data = np.copy(scan_target.proj_remissions.reshape(-1))
        viridis_range = (range_data * 255 ).astype(np.uint8)
      viridis_map = get_mpl_colormap("viridis")
      colors = viridis_map[viridis_range]

    self.back_vis.set_data(points,
                           face_color=colors[..., ::-1],
                           edge_color=colors[..., ::-1],
                           size=self.point_size)
    self.back_vis.update()

  # interface
  def key_press(self, event):
    if event.key == 'N':
      self.action = 'next'
    elif event.key == 'B':
      self.action = 'back'
    elif event.key == 'Q' or event.key == 'Escape':
      self.destroy()
      self.action = 'quit'
    elif event.key == '1':
      self.action = 'change'
      self.view_mode = 'label'
    elif event.key == '2':
      self.action = 'change'
      self.view_mode = 'range'
    elif event.key == '3':
      self.action = 'change'
      self.view_mode = 'rem'

  def get_action(self, timeout=0):
    # return action and void it to avoid reentry
    vispy.app.use_app().sleep(timeout)
    ret = self.action
    self.action = 'no'
    return ret

  def destroy(self):
    # destroy the visualization
    self.source_canvas.events.key_press.disconnect()
    self.source_canvas.close()
    if self.show_target:
      self.target_canvas.events.key_press.disconnect()
      self.target_canvas.close()
    if self.show_diff:
      self.diff_canvas.events.key_press.disconnect()
      self.diff_canvas.close()
    vispy.app.quit()
