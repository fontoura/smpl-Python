#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""
A Python implementation of the discrete event simulation environment 'smpl'.

The original 'smpl' library was developed by Myron H. MacDougall. This version
is mostly based on the C implementation of the library, which was released on
October 22, 1987. This version is also based on the C version with bugfixes
provided by Elias Procópio Duarte Júnior, and on the C version provided by
Teemu Kerola.

Authors:
    Felipe Michels Fontoura
"""

# Copyright (c) 2020 Felipe Michels Fontoura
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import sys
import math

RESERVED = 0
QUEUED = 1

class Smpl:
    """
    A discrete event simulation subsystem.
    """

    def __init__(self):
        # The pseudo-random number generator.
        self._rand = Rand()

        # Facility collection.
        self._facilities = {}

        # Next available (virtual) block number.
        self._next_block_number = 0

        # Flag which enables trace log messages.
        self._trace_enabled = False

        # Current output destination.
        self._output_stream = None

        # The initial time of the simulation.
        self._start = 0.0

        # Stream number that should be used during next initialization.
        self._next_random_number_stream = 1

        # The name of the simulation model.
        self._model_name = None

        # Available element list header (not preallocated).
        self._available_event_pool_head = None

        # Event queue header.
        self._event_queue_head = None

        # Current simulation time.
        self._clock = 0.0

        # Event code of the last event dispatched by the simulation subsystem.
        self._last_dispatched_event_code = 0

        # Token of the last event dispatched by the simulation subsystem.
        self._last_dispatched_token = None

    def init(self, model_name):
        """
        Initializes the simulation subsystem.

        This method resets all facilities, events, statistics and advances to
        the next random number stream.

        Parameters:
            model_name (string): The model name.
        """

        if model_name is None:
            raise ValueError("The model name must be provided!")

        self._output_stream = sys.stdout

        # element pool & namespace headers.
        self._next_block_number = 1

        # event list & descriptor chain headers.
        self._event_queue_head = None
        self._available_event_pool_head = None
        self._facilities = {}

        # sim., interval start, last trace times.
        self._clock = 0.0
        self._start = 0.0

        # current event no. & trace flags.
        self._last_dispatched_event_code = 0
        self._trace_enabled = False

        # save the model name.
        self._model_name = model_name

        # set the pseudo-random stream number.
        self._rand.stream(self._next_random_number_stream)
        if (self._next_random_number_stream + 1) > 15:
            self._next_random_number_stream = 1
        else:
            self._next_random_number_stream += 1

    def rand(self):
        """
        Gets the pseudo-random number generator.

        Returns:
            The pseudo-random number generator.
        """

        return self._rand

    def reset(self):
        """
        Resets all measurements taken so far.
        """

        for facility_identifier in self._facilities:
            facility_data = self._facilities[facility_identifier]
            facility_data.queue_exit_count = 0
            facility_data.preempt_count = 0
            facility_data.total_queueing_time = 0
            for server_number in range(0, len(facility_data.servers)):
                facility_server = facility_data.servers[server_number]
                facility_server.release_count = 0
                facility_server.total_busy_time = 0
        self._start = self._clock

    def mname(self):
        """
        Gets the simulation model name.

        Returns:
            The simulation model name.
        """

        return self._model_name

    def fname(self, facility_identifier):
        """
        Gets the name of a facility.

        Parameters:
            facility_identifier (FacilityIdentifier): The identifier of the facility.

        Returns:
            The name of the facility.
        """

        facility_data = self._get_facility(facility_identifier)
        return facility_data.name

    def _get_facility(self, facility_identifier):
        """
        Gets a facility.

        Parameters:
            facility_identifier (FacilityIdentifier): The identifier of the facility.

        Returns:
            The facility.
        """

        if facility_identifier is None:
            raise ValueError("The facility identifier must be provided!")

        facility_data = self._facilities[facility_identifier]
        if facility_data is None:
            raise ValueError("The facility identifier is not valid!")

        return facility_data

    def _get_blk(self, amount):
        """
        Virtually allocates a number of consecutive data blocks and returns the
        number of the first block.

        Unlike original 'smpl', this method does not actually allocate the data
        blocks, since data is not stored in data blocks but in high-level
        objects.

        Also, unlike original 'smpl', this method does not fail if the block
        pool is exhausted (since there is no actual block pool). Also, it does
        not fail if the simulation has already started.

        Parameters:
            amount (int): The amount of data blocks that should be allocated.

        Returns:
            The number of the first block.
        """

        index = self._next_block_number
        self._next_block_number += amount
        return index

    def _get_elm(self):
        """
        Gets an event descriptor.

        This method tries to get an event descriptor from the available event
        descriptor pool. If no event descriptor is available, a one is created.

        Returns:
            The event descriptor.
        """

        event_descriptor = self._available_event_pool_head
        if event_descriptor is not None:
            self._available_event_pool_head = event_descriptor.next
            event_descriptor.next = None
        else:
            block_number = self._get_blk(1)
            event_descriptor = EventDescriptor(block_number)
        return event_descriptor

    def _put_elm(self, event_descriptor):
        """
        Recycles an event descriptor which is no longer used.

        This method adds the event descriptor to the the available event
        descriptor pool.

        Parameters:
            event_descriptor (EventDescriptor): The event descriptor.
        """

        event_descriptor.next = self._available_event_pool_head
        self._available_event_pool_head = event_descriptor

    def schedule(self, event_code, time_to_event, token):
        """
        Schedules an event to be triggered at a later time.

        Parameters:
            event_code (int): A number which identifies the event type.
            token (object): An object which identifies the event target.
            time_to_event (double): The time to event, that is, how much time
            from from the current time will the event take to be triggered.
        """

        if time_to_event < 0.0 or math.isinf(time_to_event) or math.isnan(time_to_event):
            raise ValueError("The time to event must be a finite positive number!")
        if token is None:
            raise ValueError("The token must be provided!")

        event_descriptor = self._get_elm()

        event_descriptor.event_code = event_code
        event_descriptor.token = token
        event_descriptor.remaining_time_to_event = 0.0
        event_descriptor.trigger_time = self._clock + time_to_event

        self._enlist_evl(event_descriptor)

        if self._trace_enabled:
            self._msg("SCHEDULE EVENT " + event_code + " FOR TOKEN " + token)

    def cause(self):
        """
        Causes the next event in the simulated environment and returns an
        object describing it.

        This method checks which is the next event, advances the virtual time
        to the time of the event, and returns the event code-token pair.

        Unlike original 'smpl', this method does not crash is the event list is
        empty. Instead, it returns None.

        Returns:
            The event code-token pair, or None.
        """

        result = None

        if self._event_queue_head is not None:
            # delink element
            dequeued_event_descriptor = self._event_queue_head
            self._event_queue_head = dequeued_event_descriptor.next

            self._last_dispatched_event_code = dequeued_event_descriptor.event_code
            self._last_dispatched_token = dequeued_event_descriptor.token
            self._clock = dequeued_event_descriptor.trigger_time

            # return to pool
            self._put_elm(dequeued_event_descriptor)

            result = (self._last_dispatched_event_code, self._last_dispatched_token)

            if self._trace_enabled:
                self._msg("CAUSE EVENT " + self._last_dispatched_event_code + " FOR TOKEN " + self._last_dispatched_token)

        return result

    def time(self):
        """
        Gets the current time in the simulated environment.

        This value does not change until cause() is invoked.

        Returns:
            The current time in the simulated environment.
        """

        return self._clock

    def cancel(self, event_code):
        """
        Cancels an upcoming event based on its event code.

        Parameters:
            event_code (int): The event code.

        Returns:
            The token of the canceled event, or None.
        """

        token_and_time = self.remevent(event_code)

        token = None
        if token_and_time is not None:
            token = token_and_time[0]
        
        return token

    def remevent(self, event_code):
        """
        Cancels an upcoming event based on its event code.

        Parameters:
            event_code (int): The event code.

        Returns:
            The canceled event token-trigger time pair, or None.
        """

        # search for the event in the event queue.
        pred_event_descriptor = None
        succ_event_descriptor = self._event_queue_head
        while succ_event_descriptor is not None and succ_event_descriptor.event_code != event_code:
            pred_event_descriptor = succ_event_descriptor
            succ_event_descriptor = pred_event_descriptor.next

        # removes the event from the event queue.
        token_and_time = ()
        token = None
        if succ_event_descriptor is not None:
            token_and_time = (succ_event_descriptor.token, succ_event_descriptor.trigger_time)
            if self._trace_enabled:
                self._msg("CANCEL EVENT " + succ_event_descriptor.event_code + " FOR TOKEN " + token)

            if succ_event_descriptor == self._event_queue_head:
                # unlink event
                self._event_queue_head = succ_event_descriptor.next
            else:
                # list entry & deallocate it
                pred_event_descriptor.next = succ_event_descriptor.next
            self._put_elm(succ_event_descriptor)

        return token_and_time

    def unschedule(self, event_code, token):
        """
        Reverts the scheduling of an upcoming event based on its event code and
        token.

        Parameters:
            event_code (int): The event code.
            token (object): An object which identifies the event target.

        Returns:
            A boolean indicating if the event was cancelled.
        """

        # search for the event in the event queue.
        pred_event_descriptor = None
        succ_event_descriptor = self._event_queue_head
        while succ_event_descriptor is not None and (succ_event_descriptor.event_code != event_code or succ_event_descriptor.token != token):
            pred_event_descriptor = succ_event_descriptor
            succ_event_descriptor = pred_event_descriptor.next

        # removes the event from the event queue.
        cancelled = False
        if succ_event_descriptor is not None:
            cancelled = True
            if self._trace_enabled:
                self._msg("UNSCHEDULE EVENT " + succ_event_descriptor.event_code + " FOR TOKEN " + token)

            if succ_event_descriptor == self._event_queue_head:
                # unlink event
                self._event_queue_head = succ_event_descriptor.next
            else:
                # list entry & deallocate it
                pred_event_descriptor.next = succ_event_descriptor.next
            self._put_elm(succ_event_descriptor)

        return cancelled

    def _suspend(self, token):
        """
        Suspends and upcoming event.

        This method removes an event from the event queue based on the event
        token, and returns its event descriptor.

        Parameters:
            token (object): An object which identifies the event target.

        Returns:
            The event descriptor.
        """

        if token is None:
            raise ValueError("The token must be provided!")

        # search for the event in the event queue.
        pred_event_descriptor = None
        succ_event_descriptor = self._event_queue_head
        while succ_event_descriptor is not None and succ_event_descriptor.token != token:
            pred_event_descriptor = succ_event_descriptor
            succ_event_descriptor = pred_event_descriptor.next

        # if no event has been scheduled for token, an exception must be raisen.
        if succ_event_descriptor is None:
            raise ValueError("There is no event scheduled for given token!")

        # removes the event from the event queue.
        if succ_event_descriptor == self._event_queue_head:
            self._event_queue_head = succ_event_descriptor.next
        else:
            pred_event_descriptor.next = succ_event_descriptor.next

        if self._trace_enabled:
            self._msg("SUSPEND EVENT " + succ_event_descriptor.event_code + " FOR TOKEN " + token)

        return succ_event_descriptor

    def _enlist_evl(self, event_descriptor):
        """
        Adds an event descriptor to the event queue.

        Parameters:
            event_descriptor (EventDescriptor): The event descriptor.
        """

        # scan for position to insert the event descriptor.
        pred_event_descriptor = None
        succ_event_descriptor = self._event_queue_head
        while True:
            if succ_event_descriptor is None:
                # end of list
                break
            else:
                if succ_event_descriptor.trigger_time > event_descriptor.trigger_time:
                    break
            pred_event_descriptor = succ_event_descriptor
            succ_event_descriptor = pred_event_descriptor.next

        # adds the event descriptor to the list.
        event_descriptor.next = succ_event_descriptor
        if succ_event_descriptor != self._event_queue_head:
            pred_event_descriptor.next = event_descriptor
        else:
            self._event_queue_head = event_descriptor

    def _enlist_facility_evq(self, facility_data, event_descriptor):
        """
        Adds an event descriptor to the queue of a facility.

        Parameters:
            facility_data (FacilityData): The facility.
            event_descriptor (EventDescriptor): The event descriptor.
        """

        # 'head' points to head of queue/event list
        pred_event_descriptor = None
        succ_event_descriptor = facility_data.head_event_descriptor
        while True:
            # scan for position to insert entry: event list is ordered in ascending 'arg' values, queues in descending order
            if succ_event_descriptor is None:
                # end of list
                break
            else:
                succ_priority = succ_event_descriptor.priority
                priority = event_descriptor.priority

                # queue: if entry is for a preempted token (l4, the remaining event time, >0), class otherwise, insert it at the end
                if (succ_priority < priority) or ((succ_priority == priority) and (event_descriptor.remaining_time_to_event > 0.0)):
                    break
            pred_event_descriptor = succ_event_descriptor
            succ_event_descriptor = pred_event_descriptor.next

        event_descriptor.next = succ_event_descriptor
        if succ_event_descriptor != facility_data.head_event_descriptor:
            pred_event_descriptor.next = event_descriptor
        else:
            facility_data.head_event_descriptor = event_descriptor

    def facility(self, facility_name, total_servers):
        """
        Creates a facility with a given name and number of available servers.

        Parameters:
            facility_name (string): The name of the facility.
            total_servers (int): The number of servers.

        Returns:
            The unique identifier of the facility.
        """

        if facility_name is None:
            raise ValueError("The facility must have a name!")
        if total_servers <= 0:
            raise ValueError("The facility must have at least one server!")

        block_number = self._get_blk(total_servers + 2)
        new_facility_identifier = FacilityIdentifier(block_number)
        new_facility_data = FacilityData(block_number, facility_name, total_servers)

        self._facilities[new_facility_identifier] = new_facility_data

        if self._trace_enabled:
            self._msg("CREATE FACILITY " + facility_name + " WITH ID " + new_facility_identifier)

        return new_facility_identifier

    def reserve(self, facility_identifier, token, priority):
        """
        Alias for the 'request' method.
        """
        return self.request(self, facility_identifier, token, priority)

    def request(self, facility_identifier, token, priority):
        """
        Requests a facility.

        This method attempts to reserve (take ownership) over a non-busy server
        of a given facility.

        - If there is a non-busy server, this method will reserve it and return
        RESERVED.
        - If all servers are busy, this method will enqueue a request on the
        facility queue and return RESERVED. Once a server is non-busy again, an
        event - with the same cause as the last event and the provided token
        will be triggered.

        This method should probably be invoked with the same token as the
        previous event, but it is not mandatory to do so.

        Parameters:
            facility_identifier (FacilityIdentifier): Identifier of the
            facility.
            token (object): An object which identifies the event target.
            priority (int): Priority of the request. Higer values mean higher
            priority.

        Returns:
            A value indicating if a facility server was requested.
        """

        if token is None:
            raise ValueError("The token must be provided!")

        facility_data = self._get_facility(facility_identifier)
        if facility_data.busy_servers < len(facility_data.servers):
            # facility nonbusy - reserve 1st-found nonbusy server
            chosen_server = None
            for iter_server_number in range(0, len(facility_data.servers)):
                iter_server = facility_data.servers[iter_server_number]
                if iter_server.busy_token is None:
                    chosen_server = iter_server
                    break

            chosen_server.busy_token = token
            chosen_server.busy_priority = priority
            chosen_server.busy_time = self._clock

            facility_data.busy_servers+=1

            if self._trace_enabled:
                self._msg("REQUEST FACILITY " + facility_data.name + " FOR TOKEN " + token + ":  RESERVED")

            result = RESERVED
        else:
            # facility busy - enqueue token marked w/event, priority
            self._enqueue(facility_data, token, priority, self._last_dispatched_event_code, 0.0)

            if self._trace_enabled:
                self._msg("REQUEST FACILITY " + facility_data.name + " FOR TOKEN " + token + ":  QUEUED  (inq = " + facility_data.event_queue_length + ")")

            result = QUEUED

        return result

    def _enqueue(self, facility_data, token, priority, event_code, remaining_time_to_event):
        """
        Enqueues an event for a given token in a faility.

        This method enqueues a request on the queue of a facility.

        Parameters:
            facility_data (FacilityData): The facility.
            token (object): An object which identifies the event target.
            priority (int): The priority of the event.
            event_code (int): The event number.
            remaining_time_to_event (double): The remaining time to event.
        """

        facility_data.total_queueing_time += facility_data.event_queue_length * (self._clock - facility_data.time_of_last_change)
        facility_data.event_queue_length+=1
        facility_data.time_of_last_change = self._clock

        event_descriptor = self._get_elm()
        event_descriptor.token = token
        event_descriptor.event_code = event_code
        event_descriptor.remaining_time_to_event = remaining_time_to_event
        event_descriptor.priority = priority

        self._enlist_facility_evq(facility_data, event_descriptor)

    def preempt(self, facility_identifier, token, priority):
        """
        Preempts a facility.

        This method attempts to reserve (take ownership) over a server of a
        given facility, even if it's busy.

        - If there is a non-busy server, this method will reserve it and return
        RESERVED.
        - If all servers are busy, and all of them have a priority which is
        higher or the same as this request, this method will enqueue a request
        on the facility queue and return QUEUED. Once a server is non-busy
        again, an event with the same cause as the last event and the provided
        token will be triggered.
        - If all servers are busy, and at least one of them have lesser
        priority than this request, one of the servers which was requested with
        the lowest priority will be forcefully released. Also, the most recent
        event scheduled by the owner of the server (identified by its the
        token) will be suspended and added to the queue of facility. Once a
        server is available again, it will again be reserved for the previous
        owner, and the event which was previously suspended will be scheduled
        again, after the same amount of time the event had from the preemption
        time. In this case, the method will return RESERVED.

        Parameters:
            facility_identifier (FacilityIdentifier): Identifier of the
            facility.
            token (object): An object which identifies the event target.
            priority (int): Priority of the request. Higer values mean higher
            priority.

        Returns:
            A value indicating if a facility server was requested.
        """

        if token is None:
            raise ValueError("The token must be provided!")

        facility_data = self._get_facility(facility_identifier)
        chosen_server = None
        if facility_data.busy_servers < len(facility_data.servers):
            # facility nonbusy - locate 1st-found nonbusy server
            for iter_server_number in range(0, len(facility_data.servers)):
                iter_server = facility_data.servers[iter_server_number]
                if iter_server.busy_token is None:
                    chosen_server = iter_server
                    break

            result = RESERVED

            if self._trace_enabled:
                self._msg("PREEMPT FACILITY " + facility_data.name + " FOR TOKEN " + token + ":  RESERVED")
        else:
            # facility busy - find server with lowest-priority user

            # indices of server elements 1 & n
            chosen_server = facility_data.servers[0]
            for iter_server_number in range(1, len(facility_data.servers)):
                iter_server = facility_data.servers[iter_server_number]
                if iter_server.busy_priority < chosen_server.busy_priority:
                    chosen_server = iter_server

            if priority <= chosen_server.busy_priority:
                # requesting token's priority is not higher than
                # that of any user: enqueue requestor & return r=1
                self._enqueue(facility_data, token, priority, self._last_dispatched_event_code, 0.0)
                result = QUEUED
                if self._trace_enabled:
                    self._msg("PREEMPT FACILITY " + facility_data.name + " FOR TOKEN " + token + ":  QUEUED  (inq = " + facility_data.event_queue_length + ")")
            else:
                # preempt user of server k. suspend event, save
                # event number & remaining event time, & enqueue
                # preempted token. If remaining event time is 0
                # (preemption occurred at the instant release was
                # to occur, set 'te' > 0 for proper enqueueing
                # (see 'enlist'). Update facility & server stati-
                # stics for the preempted token, and set r = 0 to
                # reserve the facility for the preempting token.
                if self._trace_enabled:
                    self._msg("PREEMPT FACILITY " + facility_data.name + " FOR TOKEN " + token + ":  INTERRUPT")

                preempted_token = chosen_server.busy_token
                preempted_event_descriptor = self._suspend(preempted_token)

                event_code = preempted_event_descriptor.event_code
                time_to_event = preempted_event_descriptor.trigger_time - self._clock
                if time_to_event == 0.0:
                    time_to_event = 1.0e-99

                self._put_elm(preempted_event_descriptor)

                self._enqueue(facility_data, preempted_token, chosen_server.busy_priority, event_code, time_to_event)
                if self._trace_enabled:
                    self._msg("QUEUE FOR TOKEN " + preempted_token + " (inq = " + facility_data.event_queue_length + ")")
                    self._msg("RESERVE " + facility_data.name + " FOR TOKEN " + token + ":  RESERVED")

                chosen_server.release_count+=1
                chosen_server.total_busy_time += self._clock - chosen_server.busy_time

                facility_data.busy_servers-=1
                facility_data.preempt_count+=1
                result = RESERVED

        if result == RESERVED:
            # reserve server k of facility
            chosen_server.busy_token = token
            chosen_server.busy_priority = priority
            chosen_server.busy_time = self._clock

            facility_data.busy_servers+=1

        return result

    def release(self, facility_identifier, token):
        """
        Releases a facility.

        This method attempts to release (let go of the ownership) a busy server of a given facility.

        Parameters:
            facility_identifier (FacilityIdentifier): Identifier of the facility.
            token (object): An object which identifies the event target.
        """

        if token is None:
            raise ValueError("The token must be provided!")

        # locate server (j) reserved by releasing token
        facility_data = self._get_facility(facility_identifier)

        matching_server = None
        for iter_server_number in range(0, len(facility_data.servers)):
            iter_server = facility_data.servers[iter_server_number]
            if iter_server.busy_token == token:
                matching_server = iter_server
                break

        if matching_server is None:
            # no server reserved
            raise ValueError("There is no server reserved for the token in the facility.")

        matching_server.busy_token = None

        matching_server.release_count+=1
        matching_server.total_busy_time += self._clock - matching_server.busy_time

        facility_data.busy_servers-=1

        if self._trace_enabled:
            self._msg("RELEASE FACILITY " + facility_data.name + " FOR TOKEN " + token)

        if facility_data.event_queue_length > 0:
            # queue not empty: dequeue request ('k' = index of element) & update queue measures
            dequeued_event_descriptor = facility_data.head_event_descriptor
            facility_data.head_event_descriptor = dequeued_event_descriptor.next

            time_to_event = dequeued_event_descriptor.remaining_time_to_event
            facility_data.total_queueing_time += facility_data.event_queue_length * (self._clock - facility_data.time_of_last_change)
            facility_data.event_queue_length-=1
            facility_data.queue_exit_count+=1
            facility_data.time_of_last_change = self._clock
            if self._trace_enabled:
                self._msg("DEQUEUE FOR TOKEN " + dequeued_event_descriptor.token + "  (inq = " + facility_data.event_queue_length + ")")

            if time_to_event == 0.0:
                # blocked request: place request at head of event list (so its facility request can be re-initiated before any other requests scheduled for this time)
                dequeued_event_descriptor.trigger_time = self._clock
                dequeued_event_descriptor.next = self._event_queue_head
                self._event_queue_head = dequeued_event_descriptor

                if self._trace_enabled:
                    self._msg("RESCHEDULE EVENT " + dequeued_event_descriptor.event_code + " FOR TOKEN " + dequeued_event_descriptor.token)
            else:
                # return after preemption: reserve facility for dequeued request & reschedule remaining event time
                matching_server.busy_token = dequeued_event_descriptor.token
                matching_server.busy_priority = dequeued_event_descriptor.priority
                matching_server.busy_time = self._clock

                facility_data.busy_servers+=1

                if self._trace_enabled:
                    self._msg("RESERVE " + self.fname(facility_identifier) + " FOR TOKEN " + dequeued_event_descriptor.token)

                dequeued_event_descriptor.trigger_time = self._clock + time_to_event
                self._enlist_evl(dequeued_event_descriptor)

                if self._trace_enabled:
                    self._msg("RESUME EVENT " + dequeued_event_descriptor.event_code + " FOR TOKEN " + dequeued_event_descriptor.token)

    def status(self, facility_identifier):
        """
        Gets the status of a facility.

        This method returns True if a facility is busy (that is, if all its servers are busy).

        Parameters:
            facility_identifier (FacilityIdentifier): Identifier of the facility.

        Returns:
            A value indicating if the facility is busy.
        """

        facility_data = self._get_facility(facility_identifier)
        return facility_data.busy_servers == len(facility_data.servers)

    def qlength(self, facility_identifier):
        """
        Alias for the 'inq' method.
        """
        return self.inq(facility_identifier)

    def inq(self, facility_identifier):
        """
        Gets current queue length of a facility.

        Parameters:
            facility_identifier (FacilityIdentifier): Identifier of the
            facility.

        Returns:
            The current queue length of the facility.
        """

        facility_data = self._get_facility(facility_identifier)
        return facility_data.event_queue_length

    def U(self, facility_identifier):
        """
        Gets the utilization of a facility.

        This is the sum of the percentage of the time in which each of the
        facility servers was busy.

        Parameters:
            facility_identifier (FacilityIdentifier): Identifier of the
            facility.

        Returns:
            The current queue length of the facility.

        """

        facility_data = self._get_facility(facility_identifier)
        utilization = 0.0
        time_since_start = self._clock - self._start
        if time_since_start > 0.0:
            for server_number in range(0, len(facility_data.servers)):
                facility_server = facility_data.servers[server_number]
                utilization += facility_server.total_busy_time
            utilization /= time_since_start
        return utilization

    def B(self, facility_identifier):
        """
        Gets the mean busy time of a facility.

        The busy time of a facility server is the timespan after that ranges
        from its request to its release.

        Parameters:
            facility_identifier (FacilityIdentifier): Identifier of the
            facility.

        Returns:
            The mean busy time of the facility.
        """

        facility_data = self._get_facility(facility_identifier)
        total_releases = 0
        total_busy_time = 0.0
        for server_number in range(0, len(facility_data.servers)):
            facility_server = facility_data.servers[server_number]
            total_busy_time += facility_server.total_busy_time
            total_releases += facility_server.release_count
        return (total_busy_time / total_releases) if total_releases > 0 else total_busy_time

    def Lq(self, facility_identifier):
        """
        Gets the average queue length of a facility.

        Parameters:
            facility_identifier (FacilityIdentifier): Identifier of the
            facility.

        Returns:
            The average queue length of the facility.
        """

        facility_data = self._get_facility(facility_identifier)
        time_since_start = self._clock - self._start
        return (facility_data.total_queueing_time / time_since_start) if time_since_start > 0.0 else 0.0

    def trace(self, trace_enabled):
        """
        Turns trace on or off.

        Parameters:
            trace_enabled (bool): True if trace should be on.
        """

        self._trace_enabled = trace_enabled

    def _msg(self, message):
        """
        Prints a log message with a timestamp.

        Parameters:
            message (string): The log message.
        """

        self._output_stream.write("At time %12.3f -- %s\n" % self._clock, message)

    def report(self):
        """
        Generates a report message on the output stream.
        """

        if len(self._facilities) == 0:
            self._output_stream.write("no facilities defined:  report abandoned\n")
        else:
            self._output_stream.write("\n")
            self._output_stream.write("smpl SIMULATION REPORT\n")
            self._output_stream.write("\n")
            self._output_stream.write("\n")

            self._output_stream.write("MODEL %-56sTIME: %11.3f\n" % (self.mname(), self._clock))
            self._output_stream.write("%68s%11.3f\n" % ("INTERVAL: ", self._clock - self._start))
            self._output_stream.write("\n")
            self._output_stream.write("MEAN BUSY     MEAN QUEUE        OPERATION COUNTS\n")
            self._output_stream.write(" FACILITY          UTIL.     PERIOD        LENGTH     RELEASE   PREEMPT   QUEUE\n")

            for facility_identifier in self._facilities:
                facility_data = self._facilities[facility_identifier]

                total_releases = 0
                for server_number in range(0, len(facility_data.servers)):
                    facility_server = facility_data.servers[server_number]
                    total_releases += facility_server.release_count

                if len(facility_data.servers) == 1:
                    facility_name = facility_data.name
                else:
                    facility_name = "%s[%d]" % facility_data.name, len(facility_data.servers)

                self._output_stream.write(" %-17s%6.4f %10.3f %13.3f %11d %9d %7d\n" % (facility_name, self.U(facility_identifier), self.B(facility_identifier), self.Lq(facility_identifier), total_releases, facility_data.preempt_count, facility_data.queue_exit_count))

    def sendto(self, dest):
        """
        Redirect the output stream.

        Parameters:
            dest (stream): The output stream.
        """

        if dest is None:
            raise ValueError("The output stream must be provided!")

        self._output_stream = dest

class Rand:
    """
    A Python implementation of the pseudo-random number generator of 'smpl'.
    """

    DEFAULT_STREAMS = [ 1973272912, 747177549, 20464843, 640830765, 1098742207, 78126602, 84743774, 831312807, 124667236, 1172177002, 1124933064, 1223960546, 1878892440, 1449793615, 553303732 ]
    """
    Default seeds for streams 1-15.
    """

    A = 16807
    """
    Multiplier (7**5) for 'ranf'.
    """

    M = 2147483647
    """
    Modulus (2**31-1) for 'ranf'.
    """

    def __init__(self):
        # Seed for current stream.
        self._seed = 0

        self._normal_z2 = 0.0

    def stream(self, stream_number):
        """
        Change the current generator stream.

        Valid stream numbers range from 1 to 15.

        Parameters:
            stream_number (int): The generator stream number.
        """

        if (stream_number < 1) or (stream_number > 15):
            raise ValueError("Illegal random number generator stream!")

        self._seed = Rand.DEFAULT_STREAMS[stream_number - 1]

        self._normal_z2 = 0

    def seed(self, seed):
        """
        Change the seed for current stream.

        Parameters:
            seed (int): The seed.
        """

        self._seed = seed

    def prop(self):
        """
        Alias for the 'ranf' method.
        """
        return self.ranf()

    def ranf(self):
        """
        Generates a pseudo-random value from an uniform distribution ranging
        from 0 to 1.

        Returns:
            The generated pseudo-random number.
        """

        # The comments below are based on the original comments of 'smpl'.
        # In the comments, The lower short of I is called 'L', an the higher short of I is called 'H'.

        # 16807*H->Hi
        # [C] p=(short *)&I
        # [C] Hi=*(p+1)*A
        # (p is pointer to I)
        hi = get_short1(self._seed) * Rand.A

        # 16807*L->Lo
        # [C] *(p+1)=0
        # (p is pointer to I)
        self._seed = set_short1(self._seed, 0)

        # [C] Lo=I*A
        # (p is pointer to I)
        lo = self._seed * Rand.A

        # add high-order bits of Lo to Hi
        # [C] p=(short *)&Lo
        # [C] Hi+=*(p+1)
        # (p is pointer to Lo)
        hi += get_short1(lo)

        # low-order bits of Hi->LO
        # [C] q=(short *)&Hi
        # (q is pointer to Hi)

        # clear sign bit
        # [C] *(p+1)=*q&0X7FFF
        # (p is pointer to Lo, q is pointer to Hi)
        lo = set_short1(lo, get_short0(hi) & 0x7FFF)

        # Hi bits 31-45->K
        # [C] k=*(q+1)<<1
        # [C] if (*q&0x8000) { k++ }
        # (q is pointer to Hi)
        k = get_short1(hi) << 1
        if (get_short0(hi) & 0x8000) != 0:
            k += 1

        # form Z + K [- M] (where Z=Lo): presubtract M to avoid overflow
        lo -= Rand.M
        lo += k
        if lo < 0:
            lo += Rand.M
        self._seed = lo

        # Lo x 1/(2**31-1)
        return (lo * 4.656612875E-10)

    def uniform(self, lower, upper):
        """
        Generates a pseudo-random value from an uniform distribution.

        Parameters:
            lower (double): The lower boundary, inclusive.
            upper (double): The upper boundary, inclusive.

        Returns:
            The generated pseudo-random number.
        """

        if lower > upper:
            raise ValueError("For the uniform pseudo-random generator, the lower boundary must not exceed the upper boundary")
        return lower + (upper - lower) * self.ranf()

    def random(self, lower, upper):
        """
        Generates a pseudo-random integer in a range from an uniform
        distribution.

        Parameters:
            lower (int): The lower boundary, inclusive.
            upper (int): The upper boundary, inclusive.

        Returns:
            The generated pseudo-random integer number.
        """

        if lower > upper:
            raise ValueError("For the uniform pseudo-random generator, the lower boundary must not exceed the upper boundary")
        m = upper - lower
        d = int((m + 1.0) * self.ranf())
        return lower + d

    def expntl(self, mean):
        """
        Generates a pseudo-random value from an exponential distribution.

        Parameters:
            mean (double): The mean value.

        Returns:
            The generated pseudo-random number.
        """

        return -mean * math.log(self.ranf())

    def erlang(self, mean, std_dev):
        """
        Generates a pseudo-random value from an Erlang distribution.

        The standard deviation MUST NOT be larger than the mean.

        Parameters:
            mean (double): The mean value.
            std_dev (double): The standard deviation.

        Returns:
            The generated pseudo-random number.
        """

        if std_dev > mean:
            raise ValueError("For the Erlang pseudo-random generator, the standard deviation must not be larger than the mean value")

        z1 = mean / std_dev
        k = int(z1 * z1)
        z2 = 1.0
        for _ in range(0, k):
            z2 *= self.ranf()
        return -(mean / k) * math.log(z2)

    def hyperx(self, mean, std_dev):
        """
        Generates a pseudo-random value from a Morse's two-stage
        hyperexponential distribution.

        The standard deviation MUST be larger than the mean.

        Parameters:
            mean (double): The mean value.
            std_dev (double): The standard deviation.

        Returns:
            The generated pseudo-random number.
        """

        if std_dev <= mean:
            raise ValueError("For the hyperexponential pseudo-random generator, the standard deviation must be larger than the mean value")

        cv = std_dev / mean
        z1 = cv * cv
        p = 0.5 * (1.0 - (math.sqrt((z1 - 1.0) / (z1 + 1.0))))
        if self.ranf() > p:
            z2 = (mean / (1.0 - p))
        else:
            z2 = (mean / p)
        return -0.5 * z2 * math.log(self.ranf())

    def normal(self, mean, std_dev):
        """
        Generates a pseudo-random value from a normal distribution.

        Parameters:
            mean (double): The mean value.
            std_dev (double): The standard deviation.

        Returns:
            The generated pseudo-random number.
        """

        if self._normal_z2 != 0.0:
            # use value from previous call
            z1 = self._normal_z2
            self._normal_z2 = 0.0
        else:
            while True:
                v1 = 2.0 * self.ranf() - 1.0
                v2 = 2.0 * self.ranf() - 1.0
                w = v1 * v1 + v2 * v2
                if w < 1.0:
                    break
            w = (math.sqrt((-2.0 * math.log(w)) / w))
            z1 = v1 * w
            self._normal_z2 = v2 * w
        return mean + z1 * std_dev

class EventDescriptor:
    """
    Data regarding a scheduled (for execution) or queued (in a facility) event
    in the 'smpl' simulation subsystem.
    """

    def __init__(self, block_number):
        """
        Creates an event descriptor.

        Parameters:
            block_number (int): The block number of the event descriptor.
        """

        self._block_number = block_number
        self.next = None
        self.event_code = 0
        self.token = None
        self.remaining_time_to_event = 0.0
        self.trigger_time = 0.0
        self.priority =0

    def __str__(self):
        return "EventDescriptor(" + self._block_number + ")"

class FacilityIdentifier:
    """
    Identifier of a facility (resource) in the 'smpl' simulation subsystem.

    In the original C version of 'smpl', facilities were identified by plain
    'int' values.
    """

    def __init__(self, block_number):
        """
        Creates a facility identifier.

        Parameters:
            block_number (int): The initial block number of the facility.
        """

        self._block_number = block_number

    def __hash__(self):
        return self._block_number

    def __eq__(self, obj):
        if self is obj:
            result = True
        elif obj is None:
            result = False
        elif type(self) != type(obj):
            result = False
        else:
            result = (self._block_number == obj._block_number)
        return result

    def __str__(self):
        return "FacilityIdentifier(" + self._block_number + ")"

class FacilityData:
    """
    Data of a facility (resource) in the 'smpl' simulation subsystem.
    """

    def __init__(self, block_number, name, total_servers):
        """
        Creates an object which stores facility data.

        Parameters:
            block_number (int): The initial block number of the facility.
            name (string): The name of the facility.
            total_servers (int): The total amount of servers of the facility.
        """

        self._block_number = block_number

        self.name = name
        self.servers = [None] * total_servers
        for i in range(0, total_servers):
            self.servers[i] = FacilityServer(block_number + 2 + i)
        self.total_servers = total_servers
        self.busy_servers = 0
        self.event_queue_length = 0
        self.head_event_descriptor = None
        self.queue_exit_count = 0
        self.preempt_count = 0
        self.time_of_last_change = 0.0
        self.total_queueing_time = 0.0

    def __str__(self):
        return "FacilityData(" + self._block_number + ")"

class FacilityServer:
    """
    An instance of a facility.
    """

    def __init__(self, block_number):
        """
        Creates a facility server.

        Parameters:
            block_number (int): The block number of the facility server.
        """

        self._block_number = block_number

        self.busy_token = None
        self.busy_priority = 0
        self.busy_time = 0.0
        self.release_count = 0
        self.total_busy_time = 0.0

    def __str__(self):
        return "FacilityServer(" + self._block_number + ")"

def set_short0(int_value, short_value):
    """
    Sets the least significant short of an integer.

    Parameters:
        int_value (int): The integer.
        short_value (int): The short.

    Returns:
        The integer with the least significant short replaced.
    """

    return (int_value & 0xFFFF0000) | (short_value & 0x0000FFFF)

def set_short1(int_value, short_value):
    """
    Sets the most significant short of an integer.

    Parameters:
        int_value (int): The integer.
        short_value (int): The short.

    Returns:
        The integer with the most significant short replaced.
    """

    return (int_value & 0x0000FFFF) | ((short_value << 16) & 0xFFFF0000)

def get_short0(int_value):
    """
    Gets the least significant short of an integer.

    Parameters:
        int_value (int): The integer.

    Returns:
        The least significant short of the integer.
    """
    return int_value & 0x0000FFFF

def get_short1(int_value):
    """
    Gets the most significant short of an integer.

    Parameters:
        int_value (int): The integer.

    Returns:
        The most significant short of the integer.
    """

    return (int_value >> 16) & 0x0000FFFF
