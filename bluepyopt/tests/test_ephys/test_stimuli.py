"""bluepyopt.ephys.simulators tests"""

"""
Copyright (c) 2016, EPFL/Blue Brain Project

 This file is part of BluePyOpt <https://github.com/BlueBrain/BluePyOpt>

 This library is free software; you can redistribute it and/or modify it under
 the terms of the GNU Lesser General Public License version 3.0 as published
 by the Free Software Foundation.

 This library is distributed in the hope that it will be useful, but WITHOUT
 ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
 FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
 details.

 You should have received a copy of the GNU Lesser General Public License
 along with this library; if not, write to the Free Software Foundation, Inc.,
 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
"""

# pylint:disable=W0612

import numpy

import nose.tools as nt
from nose.plugins.attrib import attr

import bluepyopt.ephys as ephys
import testmodels.dummycells


@attr('unit')
def test_stimulus_init():
    """ephys.stimuli: test if Stimulus constructor works"""

    stim = ephys.stimuli.Stimulus()
    nt.assert_is_instance(stim, ephys.stimuli.Stimulus)


@attr('unit')
def test_NrnRampPulse_init():
    """ephys.stimuli: test if NrnRampPulse constructor works"""
    stim = ephys.stimuli.NrnRampPulse()
    nt.assert_is_instance(stim, ephys.stimuli.NrnRampPulse)


@attr('unit')
@attr('stimuli')
def test_NrnRampPulse_instantiate():
    """ephys.stimuli: test if NrnRampPulse injects correct current"""

    nrn_sim = ephys.simulators.NrnSimulator()
    dummy_cell = testmodels.dummycells.DummyCellModel1()
    icell = dummy_cell.instantiate(sim=nrn_sim)
    soma_loc = ephys.locations.NrnSeclistCompLocation(
        name=None,
        seclist_name='somatic',
        sec_index=0,
        comp_x=.5)
    recording = ephys.recordings.CompRecording(
        location=soma_loc,
        variable='v')

    ramp_amplitude_start = 0.1
    ramp_amplitude_end = 1.0
    ramp_delay = 20.0
    ramp_duration = 20.0
    total_duration = 50.0

    stim = ephys.stimuli.NrnRampPulse(
        ramp_amplitude_start=ramp_amplitude_start,
        ramp_amplitude_end=ramp_amplitude_end,
        ramp_delay=ramp_delay,
        ramp_duration=ramp_duration,
        total_duration=total_duration,
        location=soma_loc)
    stim.instantiate(sim=nrn_sim, icell=icell)

    recording.instantiate(sim=nrn_sim, icell=icell)

    stim_i_vec = nrn_sim.neuron.h.Vector()
    stim_i_vec.record(stim.iclamp._ref_i)  # pylint: disable=W0212
    nrn_sim.run(stim.total_duration)

    current = numpy.array(stim_i_vec.to_python())
    time = numpy.array(recording.response['time'])
    voltage = numpy.array(recording.response['voltage'])

    # make sure current is 0 before stimulus
    nt.assert_equal(numpy.max(
        current[numpy.where((0 <= time) & (time < ramp_delay))]), 0)

    # make sure voltage stays at v_init before stimulus
    nt.assert_equal(numpy.max(
        voltage[
            numpy.where((0 <= time)
                        & (time < ramp_delay))]), nrn_sim.neuron.h.v_init)

    # make sure current is at right amp at end of stimulus
    nt.assert_equal(
        current[numpy.where(time == ramp_delay)][-1],
        ramp_amplitude_start)
    # make sure current is at right amp at end of stimulus
    nt.assert_equal(
        current[numpy.where(time == (ramp_delay + ramp_duration))][0],
        ramp_amplitude_end)

    # make sure current is 0 after stimulus
    nt.assert_equal(numpy.max(
        current[
            numpy.where(
                (ramp_delay + ramp_duration < time)
                & (time <= total_duration))]), 0)

    # make sure voltage is correct after stimulus
    nt.assert_almost_equal(numpy.mean(
        voltage[
            numpy.where(
                (ramp_delay + ramp_duration < time)
                & (time <= total_duration))]), -57.994938389914402)

    recording.destroy()
    stim.destroy()
    dummy_cell.destroy()
