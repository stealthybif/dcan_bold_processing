#!/usr/bin/env python3

import argparse
import json
import os
import subprocess

here = os.path.dirname(os.path.realpath(__file__))
version = '4.0.0'


def _cli():
    """
    command line interface
    :return:
    """
    parser = generate_parser()
    args = parser.parse_args()

    kwargs = {
        'subject': args.subject,
        'task': args.task,
        'output_folder': args.output_folder,
        'fd_threshold': args.fd_threshold,
        'filter_order': args.filter_order,
        'lower_bpf': args.lower_bpf,
        'upper_bpf': args.upper_bpf,
        'motion_filter_type': args.motion_filter_type,
        'physio': args.physio,
        'motion_filter_option': args.motion_filter_option,
        'motion_filter_order': args.motion_filter_order,
        'band_stop_min': args.band_stop_min,
        'band_stop_max': args.band_stop_max,
        'skip_seconds': args.skip_seconds,
        'brain_radius': args.brain_radius,
        'setup': args.setup,
        'teardown': args.teardown
    }

    return interface(**kwargs)


def generate_parser(parser=None):
    """
    generates argument parser for this program.
    :param parser: if set, args are added to this parser.
    :return: ArgumentParser
    """
    if not parser:
        parser = argparse.ArgumentParser(
            prog='dcan_signal_processing.py',
            description="""
            Wraps the compiled DCAN Signal Processing Matlab script,
            version: %s.  Runs in 3 main modes:  [setup], [task],
            and [teardown].

            [setup]: creates white matter and ventricular masks for regression,
            must be run prior to task.

            [task]: runs regressions on a given task/fmri and outputs a
            corrected dtseries, along with power 2014 motion numbers in an
            hdf5 (.mat) format file.

            [teardown]: concatenates any resting state runs into a single
            dtseries.
            """ % version,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
    parser.add_argument('--subject', required=True,
                        help='subject/participant id')
    parser.add_argument('--task', required=True,
                        help='name of fmri data as used in the dcan fmri '
                             'pipeline.  For bids data it is set to "task-NAME"'
                        )
    parser.add_argument('--output-folder',
                        help='output folder which contains all files produced '
                             'by the dcan fmri-pipeline.  Used for setting up '
                             'standard inputs and outputs'
                        )
    parser.add_argument('--fd-threshold', type=float, default=0.3,
                        help='upper frame-wise displacement threshold for use '
                             'in signal regression.'
                        )
    parser.add_argument('--filter-order', type=int, default=2,
                        help='number of filter coefficients for bold bandpass '
                             'filter.'
                        )
    parser.add_argument('--lower-bpf', type=float, default=0.009,
                        help='lower cut-off frequency (Hz) for the butterworth '
                             'bandpass filter.')
    parser.add_argument('--upper-bpf', type=float, default=0.080,
                        help='upper cut-off frequency (Hz) for the butterworth '
                             'bandpass filter.')
    parser.add_argument('--motion-filter-type', choices=['notch','lp'], default=None,
                        help='type of band-stop filter to use for removing '
                             'respiratory artifact from motion regressors. '
                             'Current options are \'notch\' for a notch '
                             'filter or \'lp\' for a lowpass filter.'
                        )
    parser.add_argument('--physio',
                        help='input .tsv file containing physio data to '
                             'automatically determine motion filter '
                             'parameters. Columns, start time, and frequency '
                             'will also need to be specified. NOT IMPLEMENTED.'
                        )
    parser.add_argument('--motion-filter-option', type=int, default=5,
                        help='determines direction(s) in which to filter '
                             'respiratory artifact.'
                        )
    parser.add_argument('--motion-filter-order', type=int, default=4,
                        help='number of filter coeffecients for the band-stop '
                             'filter.'
                        )
    parser.add_argument('--band-stop-min', type=float,
                        help='lower frequency (bpm) for the band-stop '
                             'motion filter.'
                        )
    parser.add_argument('--band-stop-max', type=float,
                        help='upper frequency (bpm) for the band-stop '
                             'motion filter.'
                        )
    parser.add_argument('--skip-seconds', type=int, default=5,
                        help='number of seconds to cut off the beginning of '
                             'fmri time series.')
    parser.add_argument('--contiguous_frames', type=int, default=9,
                        help='number of contigious frames for power 2014 fd '
                             'thresholding.')
    parser.add_argument('--setup', action='store_true',
                        help='prepare white matter and ventricle masks, '
                             'must be run prior to individual task runs.'
                        )
    parser.add_argument('--teardown', action='store_true',
                        help='after tasks have completed, concatenate resting '
                             'state data and parcellate.'
                        )
    parser.add_argument('--brain-radius', type=int,
                        help='radius of brain for computation of framewise '
                             'displacement')

    return parser


def interface(subject, output_folder, task=None, fd_threshold=None,
              filter_order=None, lower_bpf=None, upper_bpf=None,
              motion_filter_type=None, motion_filter_option=None,
              motion_filter_order=None, band_stop_min=None,
              band_stop_max=None, skip_seconds=None, brain_radius=None,
              contiguous_frames=None, setup=False, teardown=None, **kwargs):
    """
    main function with 3 modes:
        setup, task, and teardown.

    setup:
    generates white matter and ventricular masks.

    task:
    Runs filtered movement regressors, calculates mean signal
    in ventricles and white matter, then calls dcan signal processing matlab
    script.

    teardown:
    concatenates resting state data and creates parcellated time series.

    :param subject: subject id
    :param output_folder: base output files folder for fmri pipeline
    :param task: name of task
    :param fd_threshold: threshold for use in signal regression
    :param filter_order: order of bold signal bandpass filter
    :param lower_bpf: lower limit of bold signal bandpass filter
    :param upper_bpf: upper limit of bold signal bandpass filter
    :param motion_filter_type: type of bandstop filter for filtering motion
    regressors.  Default: 'notch'
    :param motion_filter_option: dimensions along which to filter motion.
    Default: 1 1 1 1 1 1 (all translations and rotations)
    :param motion_filter_order: bandstop filter order
    :param band_stop_min: lower limit of motion bandstop filter
    :param band_stop_max: upper limit of motion bandstop filter
    :param skip_seconds: number of seconds to cut of beginning of task.
    :param brain_radius: radius for estimation of angular motion regressors
    :param contiguous_frames: minimum contigious frames for fd thresholding.
    :param setup: creates mask images, must be run prior to tasks.
    :param teardown: concatenates resting state data and generates parcels.
    :param kwargs: additional parameters.  Can be used to override default
    paths of inputs and outputs.
    :return:
    """
    # name should only reflect release version, not filter usage.
    version_name = 'DCANBOLDProc_v%s' % version

    # standard input and output folder locations.
    input_spec = {
        'dtseries': os.path.join(output_folder, 'MNINonLinear', 'Results',
                                 task, '%s_Atlas.dtseries.nii' % task),
        'fmri_volume': os.path.join(output_folder, 'MNINonLinear', 'Results',
                                    task, '%s.nii.gz' % task),
        'movement_regressors': os.path.join(output_folder, 'MNINonLinear',
                                            'Results', task,
                                            'Movement_Regressors.txt'),
        'segmentation': os.path.join(output_folder, 'MNINonLinear', 'ROIs',
                                     'wmparc.2.nii.gz')
    }
    input_spec.update(kwargs.get('input_spec', {}))
    output_spec = {
        'config': os.path.join(output_folder, 'MNINonLinear', 'Results', task,
                               version_name,
                               '%s_mat_config.json' % version_name),
        'output_ciftis': os.path.join(output_folder, version_name,
                                      'analyses_v2','workbench'),
        'output_dtseries': '%s_%s_Atlas.dtseries.nii' % (task, version_name),
        'output_motion_numbers': os.path.join(output_folder, 'MNINonLinear',
                                              'Results', task, version_name,
                                              'motion_numbers.txt'),
        'output_timecourses': os.path.join(output_folder, version_name,
                                      'analyses_v2','timecourses'),
        'result_dir': os.path.join(output_folder, 'MNINonLinear', 'Results',
                                   task, version_name),
        'summary_folder': os.path.join(output_folder, 'MNINonLinear',
                                       'summary_%s' % version_name),
        'vent_mask': os.path.join(output_folder, 'MNINonLinear',
                                  'vent_2mm_%s_mask_eroded.nii.gz' % subject),
        'vent_mean_signal': os.path.join(output_folder, 'MNINonLinear',
                                         'Results', task, version_name,
                                         '%s_vent_mean.txt' % task),
        'wm_mask': os.path.join(output_folder, 'MNINonLinear',
                                'wm_2mm_%s_mask_eroded.nii.gz' % subject),
        'wm_mean_signal': os.path.join(output_folder, 'MNINonLinear', 'Results',
                                       task, version_name, '%s_wm_mean.txt' %
                                       task)
    }
    output_spec.update(kwargs.get('output_spec', {}))

    if setup:
        print('removing old %s outputs' % version_name)
        # delete existing fnlpp results
        for value in output_spec.values():
            if task in value:
                continue
            elif os.path.exists(value):
                os.remove(value)

        # create the result_dir
        if not os.path.exists(output_spec['result_dir']):
            os.mkdir(output_spec['result_dir'])

        # create white matter and ventricle masks for regression
        make_masks(input_spec['segmentation'], output_spec['wm_mask'],
                   output_spec['vent_mask'])
    elif teardown:
        # setup inputs, then run analyses_v2
        repetition_time = get_repetition_time(input_spec['fmri_volume'])
        analyses_v2_config = {
                    'path_wb_c': '{CARET7DIR}/wb_command' % os.environ,
                    'epi_TR': repitition_time,
                    'summary_Dir': output_spec['summary_folder'],
                    'brain_radius_in_mm': brain_radius,
                    'expected_contiguous_frame_count': contiguous_frames,
                    'result_dir': output_spec['result_dir'],
                    'path_motion_numbers': output_spec['output_motion_numbers'],
                    'path_ciftis': output_spec['output_ciftis'],
                    'path_timecourses': output_spec['output_timecourses'],
                    'skip_seconds': skip_seconds
                }
        concat_and_parcellate()
    else:
        assert os.path.exists(output_spec['vent_mask']), \
            'must run this script with --setup flag prior to running ' \
            'individual tasks.'
        print('removing old %s outputs for %s' % (version_name, task))

        # delete existing results
        for value in output_spec.values():
            if task in value and os.path.exists(value):
                os.remove(value)

        # filter motion regressors if a bandstop filter is specified
        repetition_time = get_repetition_time(input_spec['fmri_volume'])
        if motion_filter_type:
            movreg_basename = os.path.basename(
                input_spec['movement_regressors'])
            filtered_movement_regressors = os.path.join(
                output_spec['result_dir'],
                '%s_bs%s_%s_filtered_%s' % (version_name, band_stop_min,
                                            band_stop_max, movreg_basename)
                )
            executable = os.path.join(
                here, 'bin', 'run_filtered_movement_regressors.sh')
            cmd = [executable, os.environ['MCROOT'],
                   input_spec['movement_regressors'], str(repetition_time),
                   str(motion_filter_option), str(motion_filter_order), str(band_stop_min),
                   motion_filter_type, str(band_stop_min), str(band_stop_max),
                   filtered_movement_regressors]

            subprocess.call(cmd)
            # update input movement regressors
            input_spec['movement_regressors'] = filtered_movement_regressors

        # get ventricular and white matter signals
        mean_roi_signal(input_spec['fmri_volume'], output_spec['wm_mask'],
                        output_spec['wm_mean_signal'])
        mean_roi_signal(input_spec['fmri_volume'], output_spec['vent_mask'],
                        output_spec['vent_mean_signal'])

        # run signal processing on dtseries
        matlab_input = {
            'path_wb_c': '{CARET7DIR}/wb_command' % os.environ,
            'bp_order': filter_order,
            'lp_Hz': lower_bpf,
            'hp_Hz': upper_bpf,
            'TR': repetition_time,
            'fd_th': fd_threshold,
            'path_cii': input_spec['dtseries'],
            'path_ex_sum': output_spec['summary_folder'],
            'FNL_preproc_CIFTI_name': output_spec['output_dtseries'],
            'fMRIName': task,
            'file_wm': output_spec['wm_mean_signal'],
            'file_vent': output_spec['vent_mean_signal'],
            'file_mov_reg': input_spec['movement_regressors'],
            'motion_filename': os.path.basename(
                output_spec['output_motion_numbers']),
            'skip_seconds': skip_seconds,
            'result_dir': output_spec['result_dir']
        }
        # write input json for matlab script
        with open(output_spec['config'], 'w') as fd:
            json.dump(matlab_input, fd)

        print('running %s matlab on %s' % (version_name, task))
        executable = os.path.join(here, 'bin', 'run_FNL_preproc_Matlab.sh')
        cmd = [executable, os.environ['MCRROOT'], output_spec['config']]
        subprocess.call(cmd)


def get_repetition_time(fmri):
    """
    :param fmri: path to fmri nifti.
    :return: repetition time from pixdim4
    """
    cmd = 'fslval {task} pixdim4'.format(task=fmri)
    popen = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
    stdout,stderr = popen.communicate()
    repetition_time = float(stdout)
    return repetition_time


def mean_roi_signal(fmri, mask, output):
    """
    :param fmri: path to fmri nifti
    :param mask: path to mask/roi nifti
    :param output: output text file of time series of mean values within the
    mask/roi
    :return: None
    """
    cmd = 'fslmeants -i {fmri} -o {output} -m {mask}'
    cmd = cmd.format(fmri=fmri, output=output, mask=mask)
    subprocess.call(cmd.split())


def make_masks(segmentation, wm_mask_out, vent_mask_out, **kwargs):
    """
    generates ventricular and white matter masks from a Desikan/FreeSurfer
    segmentation file.  label constraints may be overridden.
    :param segmentation: Desikan/FreeSurfer spec segmentation nifti file.
    Does not need to be a cifti but must have labels according to FS lookup
    table, including cortical parcellations.
    :param wm_mask_out: binary white matter mask.
    :param vent_mask_out: binary ventricular mask.
    :param kwargs: dictionary of label value overrides.  You may override
    default label number bounds for white matter and ventricle masks in the
    segmentation file.
    :return: None
    """

    wd = os.path.dirname(wm_mask_out)
    # set parameter defaults
    defaults = dict(wm_lt_R=2950, wm_ut_R=3050, wm_lt_L=3950, wm_ut_L=4050,
                    vent_lt_R=43, vent_ut_R=43, vent_lt_L=4, vent_ut_L=4)
    # set temporary filenames
    tempfiles = {
        'wm_mask_L': os.path.join(wd, 'tmp_left_wm.nii.gz'),
        'wm_mask_R': os.path.join(wd, 'tmp_right_wm.nii.gz'),
        'vent_mask_L': os.path.join(wd, 'tmp_left_vent.nii.gz'),
        'vent_mask_R': os.path.join(wd, 'tmp_right_vent.nii.gz'),
        'wm_mask': os.path.join(wd, 'tmp_wm.nii.gz'),
        'vent_mask': os.path.join(wd, 'tmp_vent.nii.gz')
    }
    # inputs and outputs
    iofiles = {
        'segmentation': segmentation,
        'wm_mask_out': wm_mask_out,
        'vent_mask_out': vent_mask_out
    }
    # command pipeline
    cmdlist = [
        'fslmaths {segmentation} -thr {wm_lt_R} -uthr {wm_ut_R} {wm_mask_R}',
        'fslmaths {segmentation} -thr {wm_lt_L} -uthr {wm_ut_L} {wm_mask_L}',
        'fslmaths {wm_mask_R} -add {wm_mask_L} -bin {wm_mask}',
        'fslmaths {wm_mask} -kernel gauss 2 -ero {wm_mask_out}',
        'fslmaths {segmentation} -thr {vent_lt_R} -uthr {vent_ut_R} '
        '{vent_mask_R}',
        'fslmaths {segmentation} -thr {vent_lt_L} -uthr {vent_ut_L} '
        '{vent_mask_L}',
        'fslmaths {vent_mask_R} -add {vent_mask_L} -bin {vent_mask}',
        'fslmaths {vent_mask} -kernel gauss 2 -ero {vent_mask_out}'
    ]
    # format and run commands
    defaults.update(kwargs)
    kwargs.update(defaults)
    kwargs.update(iofiles)
    kwargs.update(tempfiles)
    for cmdfmt in cmdlist:
        cmd = cmdfmt.format(**kwargs)
        subprocess.call(cmd.split())
    # cleanup
    for key in tempfiles.keys():
        os.remove(tempfiles[key])


def concat_and_parcellate(task_basenames, **kwargs):
    pass


if __name__ == '__main__':
    _cli()