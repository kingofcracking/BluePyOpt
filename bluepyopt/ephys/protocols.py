"""Protocol classes"""

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

# pylint: disable=W0511

# TODO: maybe find a better name ? -> sweep ?
import logging
logger = logging.getLogger(__name__)


class Protocol(object):

    """Class representing a protocol (stimulus and recording)."""

    def __init__(self, name=None):
        """Constructor

        Args:
            name (str): name of the feature
        """

        self.name = name


class SequenceProtocol(Protocol):

    """A protocol consisting of a sequence of other protocols"""

    def __init__(self, name=None, protocols=None):
        """Constructor

        Args:
            name (str): name of this object
            protocols (list of Protocols): subprotocols this protocol
                consists of
        """
        super(SequenceProtocol, self).__init__(name)
        self.protocols = protocols

    def run(self, cell_model, param_values, sim=None, isolate=None):
        """Instantiate protocol"""

        responses = {}

        for protocol in self.protocols:
            responses.update(
                protocol.run(
                    cell_model=cell_model,
                    param_values=param_values,
                    sim=sim,
                    isolate=isolate))

        return responses


class SweepProtocol(Protocol):

    """Sweep protocol"""

    def __init__(
            self,
            name=None,
            stimuli=None,
            recordings=None,
            cvode_active=None):
        """Constructor

        Args:
            name (str): name of this object
            stimuli (list of Stimuli): Stimulus objects used in the protocol
            recordings (list of Recordings): Recording objects used in the
                protocol
            cvode_active (bool): whether to use variable time step
        """

        super(SweepProtocol, self).__init__(name)
        self.stimuli = stimuli
        self.recordings = recordings
        self.cvode_active = cvode_active

    @property
    def total_duration(self):
        """Total duration"""

        return max([stimulus.total_duration for stimulus in self.stimuli])

    def _run_func(self, cell_model, param_values, sim=None):
        """Run protocols"""

        try:
            cell_model.freeze(param_values)
            cell_model.instantiate(sim=sim)

            self.instantiate(sim=sim, icell=cell_model.icell)

            try:
                sim.run(self.total_duration, cvode_active=self.cvode_active)
            except RuntimeError:
                logger.debug(
                    'SweepProtocol: Running of parameter set {%s} generated '
                    'RuntimeError, returning None in responses',
                    str(param_values))
                responses = {recording.name:
                             None for recording in self.recordings}
            else:
                responses = {
                    recording.name: recording.response
                    for recording in self.recordings}

            self.destroy()
            for recording in self.recordings:
                recording.destroy()

            for stimulus in self.stimuli:
                stimulus.destroy()

            cell_model.destroy()

            cell_model.unfreeze(param_values.keys())

            return responses
        except:
            import sys
            import traceback
            raise Exception(
                "".join(
                    traceback.format_exception(*sys.exc_info())))

    def run(self, cell_model, param_values, sim=None, isolate=None):
        """Instantiate protocol"""

        if isolate is None:
            isolate = True

        if isolate:
            def _reduce_method(meth):
                """Overwrite reduce"""
                return (getattr, (meth.__self__, meth.__func__.__name__))

            import copy_reg
            import types
            copy_reg.pickle(types.MethodType, _reduce_method)

            import multiprocessing

            pool = multiprocessing.Pool(1, maxtasksperchild=1)
            responses = pool.apply(
                self._run_func,
                kwds={
                    'cell_model': cell_model,
                    'param_values': param_values,
                    'sim': sim})

            pool.terminate()
            pool.join()
            del pool
        else:
            responses = self._run_func(
                cell_model=cell_model,
                param_values=param_values,
                sim=sim)

        return responses

    def instantiate(self, sim=None, icell=None):
        """Instantiate"""

        for stimulus in self.stimuli:
            stimulus.instantiate(sim=sim, icell=icell)

        for recording in self.recordings:
            recording.instantiate(sim=sim, icell=icell)

    def destroy(self):
        """Destroy protocol"""

        for stimulus in self.stimuli:
            stimulus.destroy()

        for recording in self.recordings:
            recording.destroy()

    def __str__(self):
        """String representation"""

        content = '%s:\n' % self.name

        content += '  stimuli:\n'
        for stimulus in self.stimuli:
            content += '    %s\n' % str(stimulus)

        content += '  recordings:\n'
        for recording in self.recordings:
            content += '    %s\n' % str(recording)

        return content
