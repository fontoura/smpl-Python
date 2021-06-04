#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""
A Python implementation of the discrete event simulation environment 'smpl'.

The original 'smpl' library was developed by Myron H. MacDougall. This version is mostly based on the C implementation of the library, which was released on October 22, 1987. This version is also based on the C version with bugfixes provided by Elias Procópio Duarte Júnior, and on the C version provided by Teemu Kerola.

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
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
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
        self._nextBlockNumber = 0
        
        # Flag which enables trace log messages.
        self._traceEnabled = False
        
        # Current output destination.
        self._outputStream = None
        
        # The initial time of the simulation.
        self._start = 0.0
        
        # Stream number that should be used during next initialization.
        self._nextRandomNumberStream = 1
        
        # The name of the simulation model.
        self._modelName = None
        
        # Available element list header (not preallocated).
        self._availableEventPoolHead = None
        
        # Event queue header.
        self._eventQueueHead = None
        
        # Current simulation time.
        self._clock = 0.0
        
        # Event code of the last event dispatched by the simulation subsystem.
        self._lastDispatchedEventCode = 0
        
        # Token of the last event dispatched by the simulation subsystem.
        self._lastDispatchedToken = None
    
    def init(self, s):
        """
        Initializes the simulation subsystem.
        
        This method resets all facilities, events, statistics and advances to the next random number stream.
        
        Parameters:
            s (string): The model name.
        """
        
        if s is None:
            raise ValueError("The model name must be provided!")
        
        self._outputStream = sys.stdout

        # element pool & namespace headers.
        self._nextBlockNumber = 1
        
        # event list & descriptor chain headers.
        self._eventQueueHead = None
        self._availableEventPoolHead = None
        self._facilities = {}
        
        # sim., interval start, last trace times.
        self._clock = 0.0
        self._start = 0.0
        
        # current event no. & trace flags.
        self._lastDispatchedEventCode = 0
        self._traceEnabled = False
        
        # save the model name.
        self._modelName = s
        
        # set the pseudo-random stream number.
        self._rand.stream(self._nextRandomNumberStream)
        self._nextRandomNumberStream = 1 if (self._nextRandomNumberStream + 1) > 15 else self._nextRandomNumberStream
    
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
        
        for facilityIdentifier in self._facilities:
            facilityData = self._facilities[facilityIdentifier]
            facilityData.queueExitCount = 0
            facilityData.preemptCount = 0
            facilityData.totalQueueingTime = 0
            for serverNumber in range(0, len(facilityData.servers)):
                facilityServer = facilityData.servers[serverNumber]
                facilityServer.releaseCount = 0
                facilityServer.totalBusyTime = 0
        self._start = self._clock
    
    def mname(self):
        """
        Gets the simulation model name.
        
        Returns:
            The simulation model name.
        """
        
        return self._modelName
    
    def fname(self, facilityIdentifier):
        """
        Gets the name of a facility.
        
        Parameters:
            facilityIdentifier (FacilityIdentifier): The identifier of the facility.
        
        Returns:
            The name of the facility.
        """
        
        facilityData = self._get_facility(facilityIdentifier)
        return facilityData.name
    
    def _get_facility(self, facilityIdentifier):
        """
        Gets a facility.
        
        Parameters:
            facilityIdentifier (FacilityIdentifier): The identifier of the facility.
        
        Returns:
            The facility.
        """
        
        if facilityIdentifier is None:
            raise ValueError("The facility identifier must be provided!")
        
        facilityData = self._facilities[facilityIdentifier]
        if facilityData is None:
            raise ValueError("The facility identifier is not valid!")
        
        return facilityData

    def _get_blk(self, n):
        """
        Virtually allocates a number of consecutive data blocks and returns the number of the first block.
        
        Unlike original 'smpl', this method does not actually allocate the data blocks, since data is not stored in data blocks but in high-level objects.
        
        Also, unlike original 'smpl', this method does not fail if the block pool is exhausted (since there is no actual block pool). Also, it does not fail if the simulation has already started.
        
        Parameters:
            n (int): The amount of data blocks that should be allocated.
        
        Returns:
            The number of the first block.
        """
        
        index = self._nextBlockNumber
        self._nextBlockNumber += n
        return index
    
    def _get_elm(self):
        """
        Gets an event descriptor.
        
        This method tries to get an event descriptor from the available event descriptor pool. If no event descriptor is available, a one is created.
        
        Returns:
            The event descriptor.
        """
        
        eventDescriptor = self._availableEventPoolHead
        if eventDescriptor is not None:
            self._availableEventPoolHead = eventDescriptor.next
            eventDescriptor.next = None
        else:
            blockNumber = self._get_blk(1)
            eventDescriptor = EventDescriptor(blockNumber)
        return eventDescriptor
    
    def _put_elm(self, eventDescriptor):
        """
        Recycles an event descriptor which is no longer used.
        
        This method adds the event descriptor to the the available event descriptor pool.
        
        Parameters:
            eventDescriptor (EventDescriptor): The event descriptor.
        """
        
        eventDescriptor.next = self._availableEventPoolHead
        self._availableEventPoolHead = eventDescriptor
    
    def schedule(self, eventCode, te, token):
        """
        Schedules an event to be triggered at a later time.
        
        Parameters:
            eventCode (int): A number which identifies the event type.
            token (object): An object which identifies the event target.
            te (double): The time to event, that is, how much time from from the current time will the event take to be triggered.
        """
        
        if te < 0.0 or math.isinf(te) or math.isnan(te):
            raise ValueError("The time to event must be a finite positive number!")
        if token is None:
            raise ValueError("The token must be provided!")
        
        eventDescriptor = self._get_elm()
        
        eventDescriptor.eventCode = eventCode
        eventDescriptor.token = token
        eventDescriptor.remainingTimeToEvent = 0.0
        eventDescriptor.triggerTime = self._clock + te
        
        self._enlist_evl(eventDescriptor)

        if self._traceEnabled:
            self._msg("SCHEDULE EVENT " + eventCode + " FOR TOKEN " + token)
    
    def cause(self):
        """
        Causes the next event in the simulated environment and returns an object describing it.
        
        This method checks which is the next event, advances the virtual time to the time of the event, and returns the event code-token pair.
        
        Unlike original 'smpl', this method does not crash is the event list is empty. Rather, it returns None.
        
        Returns:
            The event code-token pair.
        """
        
        result = None
        
        if self._eventQueueHead is not None:
            # delink element
            dequeuedEventDescriptor = self._eventQueueHead
            self._eventQueueHead = dequeuedEventDescriptor.next
            
            self._lastDispatchedEventCode = dequeuedEventDescriptor.eventCode
            self._lastDispatchedToken = dequeuedEventDescriptor.token
            self._clock = dequeuedEventDescriptor.triggerTime
            
            # return to pool
            self._put_elm(dequeuedEventDescriptor)
            
            result = (self._lastDispatchedEventCode, self._lastDispatchedToken)

            if self._traceEnabled:
                self._msg("CAUSE EVENT " + self._lastDispatchedEventCode + " FOR TOKEN " + self._lastDispatchedToken)
        
        return result

    def time(self):
        """
        Gets the current time in the simulated environment.
        
        This value does not change until cause() is invoked.
        
        Returns:
            The current time in the simulated environment.
        """
        
        return self._clock
    
    def cancel(self, eventCode):
        """
        Cancels an upcoming event based on its event code.
        
        Parameters:
            eventCode (int): The event code.
        
        Returns:
            The token of the canceled event, or None.
        """
        
        # search for the event in the event queue.
        predEventDescriptor = None
        succEventDescriptor = self._eventQueueHead
        while succEventDescriptor is not None and succEventDescriptor.eventCode != eventCode:
            predEventDescriptor = succEventDescriptor
            succEventDescriptor = predEventDescriptor.next
        
        # removes the event from the event queue.
        token = None
        if succEventDescriptor is not None:
            token = succEventDescriptor.token
            if self._traceEnabled:
                self._msg("CANCEL EVENT " + succEventDescriptor.eventCode + " FOR TOKEN " + token)
            
            if succEventDescriptor == self._eventQueueHead:
                # unlink event
                self._eventQueueHead = succEventDescriptor.next
            else:
                # list entry & deallocate it
                predEventDescriptor.next = succEventDescriptor.next
            self._put_elm(succEventDescriptor)
        
        return token
    
    def unschedule(self, eventCode, token):
        """
        Reverts the scheduling of an upcoming event based on its event code and token.
        
        Parameters:
            eventCode (int): The event code.
            token (object): An object which identifies the event target.
        
        Returns:
            A boolean indicating if the event was cancelled.
        """
        
        # search for the event in the event queue.
        predEventDescriptor = None
        succEventDescriptor = self._eventQueueHead
        while succEventDescriptor is not None and (succEventDescriptor.eventCode != eventCode or succEventDescriptor.token != token):
            predEventDescriptor = succEventDescriptor
            succEventDescriptor = predEventDescriptor.next
        
        # removes the event from the event queue.
        cancelled = False
        if succEventDescriptor is not None:
            cancelled = True
            if self._traceEnabled:
                self._msg("UNSCHEDULE EVENT " + succEventDescriptor.eventCode + " FOR TOKEN " + token)
            
            if succEventDescriptor == self._eventQueueHead:
                # unlink event
                self._eventQueueHead = succEventDescriptor.next
            else:
                # list entry & deallocate it
                predEventDescriptor.next = succEventDescriptor.next
            self._put_elm(succEventDescriptor)
        
        return cancelled
    
    def _suspend(self, token):
        """
        Suspends and upcoming event.
        
        This method removes an event from the event queue based on the event token, and returns its event descriptor.
        
        Parameters:
            token (object): An object which identifies the event target.
        
        Returns:
            The event descriptor.
        """
        
        if token is None:
            raise ValueError("The token must be provided!")
        
        # search for the event in the event queue.
        predEventDescriptor = None
        succEventDescriptor = self._eventQueueHead
        while succEventDescriptor is not None and succEventDescriptor.token != token:
            predEventDescriptor = succEventDescriptor
            succEventDescriptor = predEventDescriptor.next
        
        # if no event has been scheduled for token, an exception must be raisen.
        if succEventDescriptor is None:
            raise ValueError("There is no event scheduled for given token!")
        
        # removes the event from the event queue.
        if succEventDescriptor == self._eventQueueHead:
            self._eventQueueHead = succEventDescriptor.next
        else:
            predEventDescriptor.next = succEventDescriptor.next
        
        if self._traceEnabled:
            self._msg("SUSPEND EVENT " + succEventDescriptor.eventCode + " FOR TOKEN " + token)
        
        return succEventDescriptor

    def _enlist_evl(self, eventDescriptor):
        """
        Adds an event descriptor to the event queue.
        
        Parameters:
            eventDescriptor (EventDescriptor): The event descriptor.
        """
        
        # scan for position to insert the event descriptor.
        predEventDescriptor = None
        succEventDescriptor = self._eventQueueHead
        while True:
            if succEventDescriptor is None:
                # end of list
                break
            else:
                if succEventDescriptor.triggerTime > eventDescriptor.triggerTime:
                    break
            predEventDescriptor = succEventDescriptor
            succEventDescriptor = predEventDescriptor.next
        
        # adds the event descriptor to the list.
        eventDescriptor.next = succEventDescriptor
        if succEventDescriptor != self._eventQueueHead:
            predEventDescriptor.next = eventDescriptor
        else:
            self._eventQueueHead = eventDescriptor
    
    def _enlist_facilityEvq(self, facilityData, eventDescriptor):
        """
        Adds an event descriptor to the queue of a facility.
        
        Parameters:
            facilityData (FacilityData): The facility.
            eventDescriptor (EventDescriptor): The event descriptor.
        """
        
        # 'head' points to head of queue/event list
        predEventDescriptor = None
        succEventDescriptor = facilityData.headEventDescriptor
        while True:
            # scan for position to insert entry: event list is ordered in ascending 'arg' values, queues in descending order
            if succEventDescriptor is None:
                # end of list
                break
            else:
                v = succEventDescriptor.priority
                arg = eventDescriptor.priority
                
                # queue: if entry is for a preempted token (l4, the remaining event time, >0), class otherwise, insert it at the end
                if (v < arg) or ((v == arg) and (eventDescriptor.remainingTimeToEvent > 0.0)):
                    break
            predEventDescriptor = succEventDescriptor
            succEventDescriptor = predEventDescriptor.next
        
        eventDescriptor.next = succEventDescriptor
        if succEventDescriptor != facilityData.headEventDescriptor:
            predEventDescriptor.next = eventDescriptor
        else:
            facilityData.headEventDescriptor = eventDescriptor
    
    def facility(self, facilityName, totalServers):
        """
        Creates a facility with a given name and number of available servers.
        
        Parameters:
            facilityName (string): The name of the facility.
            totalServers (int): The number of servers.
        
        Returns:
            The unique identifier of the facility.
        """
        
        if facilityName is None:
            raise ValueError("The facility must have a name!")
        if totalServers <= 0:
            raise ValueError("The facility must have at least one server!")
        
        blockNumber = self._get_blk(totalServers + 2)
        newFacilityIdentifier = FacilityIdentifier(blockNumber)
        newFacilityData = FacilityData(blockNumber, facilityName, totalServers)
        
        self._facilities[newFacilityIdentifier] = newFacilityData

        if self._traceEnabled:
            self._msg("CREATE FACILITY " + facilityName + " WITH ID " + newFacilityIdentifier)
        
        return newFacilityIdentifier

    def request(self, facilityIdentifier, token, priority):
        """
        Requests a facility.
        
        This method attempts to reserve (take ownership) over a non-busy server of a given facility.
        
        - If there is a non-busy server, this method will reserve it and return RESERVED.
        - If all servers are busy, this method will enqueue a request on the facility queue and return RESERVED. Once a server is non-busy again, an event - with the same cause as the last event and the provided token will be triggered.
        
        This method should probably be invoked with the same token as the previous event, but it is not mandatory to do so.
        
        Parameters:
            facilityIdentifier (FacilityIdentifier): Identifier of the facility.
            token (object): An object which identifies the event target.
            priority (int): Priority of the request. Lower numbers mean higher priority.
        
        Returns:
            A value indicating if a facility server was requested.
        """
        
        if token is None:
            raise ValueError("The token must be provided!")

        facilityData = self._get_facility(facilityIdentifier)
        if facilityData.busyServers < len(facilityData.servers):
            # facility nonbusy - reserve 1st-found nonbusy server
            chosenServer = None
            for iterServerNumber in range(0, len(facilityData.servers)):
                iterServer = facilityData.servers[iterServerNumber]
                if iterServer.busyToken is None:
                    chosenServer = iterServer
                    break
            
            chosenServer.busyToken = token
            chosenServer.busyPriority = priority
            chosenServer.busyTime = self._clock
            
            facilityData.busyServers+=1

            if self._traceEnabled:
                self._msg("REQUEST FACILITY " + facilityData.name + " FOR TOKEN " + token + ":  RESERVED")
            
            result = RESERVED
        else:
            # facility busy - enqueue token marked w/event, priority
            self._enqueue(facilityData, token, priority, self._lastDispatchedEventCode, 0.0)
            
            if self._traceEnabled:
                self._msg("REQUEST FACILITY " + facilityData.name + " FOR TOKEN " + token + ":  QUEUED  (inq = " + facilityData.eventQueueLength + ")")
            
            result = QUEUED

        return result
    
    def _enqueue(self, facilityData, token, pri, ev, te):
        """
        Enqueues an event for a given token in a faility.
        
        This method enqueues a request on the queue of a facility.
        
        Parameters:
            facilityData (FacilityData): The facility.
            token (object): An object which identifies the event target.
            pri (int): The priority of the event.
            ev (int): The event number.
            te (double): The remaining time to event.
        """
        
        facilityData.totalQueueingTime += facilityData.eventQueueLength * (self._clock - facilityData.timeOfLastChange)
        facilityData.eventQueueLength+=1
        facilityData.timeOfLastChange = self._clock
        
        eventDescriptor = self._get_elm()
        eventDescriptor.token = token
        eventDescriptor.eventCode = ev
        eventDescriptor.remainingTimeToEvent = te
        eventDescriptor.priority = pri
        
        self._enlist_facilityEvq(facilityData, eventDescriptor)

    def preempt(self, facilityIdentifier, token, priority):
        """
        Preempts a facility.
        
        This method attempts to reserve (take ownership) over a server of a given facility, even if it's busy.
        
        - If there is a non-busy server, this method will reserve it and return RESERVED.
        - If all servers are busy, and all of them have a priority which is higher or the same as this request, this method will enqueue a request on the facility queue and return QUEUED. Once a server is non-busy again, an event with the same cause as the last event and the provided token will be triggered.
        - If all servers are busy, and at least one of them have lesser priority than this request, one of the servers which was requested with the lowest priority will be forcefully released. Also, the most recent event scheduled by the owner of the server (identified by its the token) will be suspended and added to the queue of facility. Once a server is available again, it will again be reserved for the previous owner, and the event which was previously suspended will be scheduled again, after the same amount of time the event had from the preemption time. In this case, the method will return RESERVED.
        
        Parameters:
            facilityIdentifier (FacilityIdentifier): Identifier of the facility.
            token (object): An object which identifies the event target.
            priority (int): Priority of the request. Lower numbers mean higher priority.
        
        Returns:
            A value indicating if a facility server was requested.
        """
        
        if token is None:
            raise ValueError("The token must be provided!")
        
        facilityData = self._get_facility(facilityIdentifier)
        chosenServer = None
        if facilityData.busyServers < len(facilityData.servers):
            # facility nonbusy - locate 1st-found nonbusy server
            for iterServerNumber in range(0, len(facilityData.servers)):
                iterServer = facilityData.servers[iterServerNumber]
                if iterServer.busyToken is None:
                    chosenServer = iterServer
                    break
            
            result = RESERVED

            if self._traceEnabled:
                self._msg("PREEMPT FACILITY " + facilityData.name + " FOR TOKEN " + token + ":  RESERVED")
        else:
            # facility busy - find server with lowest-priority user
            
            # indices of server elements 1 & n
            chosenServer = facilityData.servers[0]
            for iterServerNumber in range(1, len(facilityData.servers)):
                iterServer = facilityData.servers[iterServerNumber]
                if iterServer.busyPriority < chosenServer.busyPriority:
                    chosenServer = iterServer
            
            if priority <= chosenServer.busyPriority:
                # requesting token's priority is not higher than
                # that of any user: enqueue requestor & return r=1
                self._enqueue(facilityData, token, priority, self._lastDispatchedEventCode, 0.0)
                result = QUEUED
                if self._traceEnabled:
                    self._msg("PREEMPT FACILITY " + facilityData.name + " FOR TOKEN " + token + ":  QUEUED  (inq = " + facilityData.eventQueueLength + ")")
            else:
                # preempt user of server k. suspend event, save
                # event number & remaining event time, & enqueue
                # preempted token. If remaining event time is 0
                # (preemption occurred at the instant release was
                # to occur, set 'te' > 0 for proper enqueueing
                # (see 'enlist'). Update facility & server stati-
                # stics for the preempted token, and set r = 0 to
                # reserve the facility for the preempting token.
                if self._traceEnabled:
                    self._msg("PREEMPT FACILITY " + facilityData.name + " FOR TOKEN " + token + ":  INTERRUPT")
                
                preemptedToken = chosenServer.busyToken
                preemptedEventDescriptor = self._suspend(preemptedToken)
                
                ev = preemptedEventDescriptor.eventCode
                te = preemptedEventDescriptor.triggerTime - self._clock
                if te == 0.0:
                    te = 1.0e-99
                
                self._put_elm(preemptedEventDescriptor)

                self._enqueue(facilityData, preemptedToken, chosenServer.busyPriority, ev, te)
                if self._traceEnabled:
                    self._msg("QUEUE FOR TOKEN " + preemptedToken + " (inq = " + facilityData.eventQueueLength + ")")
                    self._msg("RESERVE " + facilityData.name + " FOR TOKEN " + token + ":  RESERVED")
                
                chosenServer.releaseCount+=1
                chosenServer.totalBusyTime += self._clock - chosenServer.busyTime
                
                facilityData.busyServers-=1
                facilityData.preemptCount+=1
                result = RESERVED
        
        if result == RESERVED:
            # reserve server k of facility
            chosenServer.busyToken = token
            chosenServer.busyPriority = priority
            chosenServer.busyTime = self._clock
            
            facilityData.busyServers+=1

        return result
    
    def release(self, facilityIdentifier, token):
        """
        Releases a facility.
        
        This method attempts to release (let go of the ownership) a busy server of a given facility.
        
        Parameters:
            facilityIdentifier (FacilityIdentifier): Identifier of the facility.
            token (object): An object which identifies the event target.
        """
        
        if token is None:
            raise ValueError("The token must be provided!")
        
        # locate server (j) reserved by releasing token
        facilityData = self._get_facility(facilityIdentifier)
        
        matchingServer = None
        for iterServerNumber in range(0, len(facilityData.servers)):
            iterServer = facilityData.servers[iterServerNumber]
            if iterServer.busyToken == token:
                matchingServer = iterServer
                break
        
        if matchingServer is None:
            # no server reserved
            raise ValueError("There is no server reserved for the token in the facility.")
        
        matchingServer.busyToken = None

        matchingServer.releaseCount+=1
        matchingServer.totalBusyTime += self._clock - matchingServer.busyTime
        
        facilityData.busyServers-=1

        if self._traceEnabled:
            self._msg("RELEASE FACILITY " + facilityData.name + " FOR TOKEN " + token)
        
        if facilityData.eventQueueLength > 0:
            # queue not empty: dequeue request ('k' = index of element) & update queue measures
            dequeuedEventDescriptor = facilityData.headEventDescriptor
            facilityData.headEventDescriptor = dequeuedEventDescriptor.next
            
            te = dequeuedEventDescriptor.remainingTimeToEvent
            facilityData.totalQueueingTime += facilityData.eventQueueLength * (self._clock - facilityData.timeOfLastChange)
            facilityData.eventQueueLength-=1
            facilityData.queueExitCount+=1
            facilityData.timeOfLastChange = self._clock
            if self._traceEnabled:
                self._msg("DEQUEUE FOR TOKEN " + dequeuedEventDescriptor.token + "  (inq = " + facilityData.eventQueueLength + ")")
            
            if te == 0.0:
                # blocked request: place request at head of event list (so its facility request can be re-initiated before any other requests scheduled for this time)
                dequeuedEventDescriptor.triggerTime = self._clock
                dequeuedEventDescriptor.next = self._eventQueueHead
                self._eventQueueHead = dequeuedEventDescriptor
                
                if self._traceEnabled:
                    self._msg("RESCHEDULE EVENT " + dequeuedEventDescriptor.eventCode + " FOR TOKEN " + dequeuedEventDescriptor.token)
            else:
                # return after preemption: reserve facility for dequeued request & reschedule remaining event time
                matchingServer.busyToken = dequeuedEventDescriptor.token
                matchingServer.busyPriority = dequeuedEventDescriptor.priority
                matchingServer.busyTime = self._clock
                
                facilityData.busyServers+=1

                if self._traceEnabled:
                    self._msg("RESERVE " + self.fname(facilityIdentifier) + " FOR TOKEN " + dequeuedEventDescriptor.token)
                
                dequeuedEventDescriptor.triggerTime = self._clock + te
                self._enlist_evl(dequeuedEventDescriptor)
                
                if self._traceEnabled:
                    self._msg("RESUME EVENT " + dequeuedEventDescriptor.eventCode + " FOR TOKEN " + dequeuedEventDescriptor.token)
    
    def status(self, facilityIdentifier):
        """
        Gets the status of a facility.
        
        This method returns True if a facility is busy (that is, if all its servers are busy).
        
        Parameters:
            facilityIdentifier (FacilityIdentifier): Identifier of the facility.
        
        Returns:
            A value indicating if the facility is busy.
        """
        
        facilityData = self._get_facility(facilityIdentifier)
        return facilityData.busyServers == len(facilityData.servers)
    
    def inq(self, facilityIdentifier):
        """
        Gets current queue length of a facility.
        
        Parameters:
            facilityIdentifier (FacilityIdentifier): Identifier of the facility.
        
        Returns:
            The current queue length of the facility.
        """
        
        facilityData = self._get_facility(facilityIdentifier)
        return facilityData.eventQueueLength
    
    def U(self, facilityIdentifier):
        """
        Gets the utilization of a facility.
        
        This is the sum of the percentage of the time in which each of the facility servers was busy.
        
        Parameters:
            facilityIdentifier (FacilityIdentifier): Identifier of the facility.
        
        Returns:
            The current queue length of the facility.
        
        """
        
        facilityData = self._get_facility(facilityIdentifier)
        b = 0.0
        t = self._clock - self._start
        if t > 0.0:
            for serverNumber in range(0, len(facilityData.servers)):
                facilityServer = facilityData.servers[serverNumber]
                b += facilityServer.totalBusyTime
            b /= t
        return b
    
    def B(self, facilityIdentifier):
        """
        Gets the mean busy time of a facility.
        
        The busy time of a facility server is the timespan after that ranges from its request to its release.
        
        Parameters:
            facilityIdentifier (FacilityIdentifier): Identifier of the facility.
        
        Returns:
            The mean busy time of the facility.
        """
        
        facilityData = self._get_facility(facilityIdentifier)
        n = 0
        b = 0.0
        for serverNumber in range(0, len(facilityData.servers)):
            facilityServer = facilityData.servers[serverNumber]
            b += facilityServer.totalBusyTime
            n += facilityServer.releaseCount
        return (b / n) if n > 0 else b
    
    def Lq(self, facilityIdentifier):
        """
        Gets the average queue length of a facility.
        
        Parameters:
            facilityIdentifier (FacilityIdentifier): Identifier of the facility.
        
        Returns:
            The average queue length of the facility.
        """
        
        facilityData = self._get_facility(facilityIdentifier)
        t = self._clock - self._start
        return (facilityData.totalQueueingTime / t) if t > 0.0 else 0.0
    
    def trace(self, n):
        """
        Turns trace on or off.
        
        Parameters:
            n (bool): True if trace should be on.
        """
        
        self._traceEnabled = n
    
    def _msg(self, message):
        """
        Prints a log message with a timestamp.
        
        Parameters:
            message (string): The log message.
        """
        
        self._outputStream.write("At time %12.3f -- %s\n" % self._clock, message)
    
    def report(self):
        """
        Generates a report message on the output stream.
        """
        
        if len(self._facilities) == 0:
            self._outputStream.write("no facilities defined:  report abandoned\n")
        else:
            self._outputStream.write("\n")
            self._outputStream.write("smpl SIMULATION REPORT\n")
            self._outputStream.write("\n")
            self._outputStream.write("\n")
            
            self._outputStream.write("MODEL %-56sTIME: %11.3f\n" % (self.mname(), self._clock))
            self._outputStream.write("%68s%11.3f\n" % ("INTERVAL: ", self._clock - self._start))
            self._outputStream.write("\n")
            self._outputStream.write("MEAN BUSY     MEAN QUEUE        OPERATION COUNTS\n")
            self._outputStream.write(" FACILITY          UTIL.     PERIOD        LENGTH     RELEASE   PREEMPT   QUEUE\n")
            
            for facilityIdentifier in self._facilities:
                facilityData = self._facilities[facilityIdentifier]
                
                n = 0
                for serverNumber in range(0, len(facilityData.servers)):
                    facilityServer = facilityData.servers[serverNumber]
                    n += facilityServer.releaseCount
                
                if len(facilityData.servers) == 1:
                    fn = facilityData.name
                else:
                    fn = "%s[%d]" % facilityData.name, len(facilityData.servers)
                
                self._outputStream.write(" %-17s%6.4f %10.3f %13.3f %11d %9d %7d\n" % (fn, self.U(facilityIdentifier), self.B(facilityIdentifier), self.Lq(facilityIdentifier), n, facilityData.preemptCount, facilityData.queueExitCount))

    def sendto(self, dest):
        """
        Redirect the output stream.
        
        Parameters:
            dest (stream): The output stream.
        """
        
        if dest is None:
            raise ValueError("The output stream must be provided!")
        
        self._outputStream = dest

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
        self._I = 0
        
        self._normal_z2 = 0.0
    
    def stream(self, n):
        """
        Change the current generator stream.
        
        Valid stream numbers range from 1 to 15.
        
        Parameters:
            n (int): The generator stream number.
        """
        
        if (n < 1) or (n > 15):
            raise ValueError("Illegal random number generator stream!")
        
        self._I = Rand.DEFAULT_STREAMS[n - 1]
        
        self._normal_z2 = 0
    
    def seed(self, Ik):
        """
        Change the seed for current stream.
        
        Parameters:
            Ik (int): The seed.
        """
        
        self._I = Ik
    
    def ranf(self):
        """
        Generates a pseudo-random value from a normal distribution ranging from 0 to 1.
        
        Returns:
            The generated pseudo-random number.
        """
        
        # The comments below are based on the original comments of 'smpl'.
        # In the comments, The lower short of I is called 'L', an the higher short of I is called 'H'.
        
        # 16807*H->Hi
        # [C] p=(short *)&I
        # [C] Hi=*(p+1)*A
        # (p is pointer to I)
        Hi = Rand._getShort1(self._I) * Rand.A
        
        # 16807*L->Lo
        # [C] *(p+1)=0
        # (p is pointer to I)
        self._I = Rand._setShort1(self._I, 0)
        
        # [C] Lo=I*A
        # (p is pointer to I)
        Lo = self._I * Rand.A
        
        # add high-order bits of Lo to Hi
        # [C] p=(short *)&Lo
        # [C] Hi+=*(p+1)
        # (p is pointer to Lo)
        Hi += Rand._getShort1(Lo)
        
        # low-order bits of Hi->LO
        # [C] q=(short *)&Hi
        # (q is pointer to Hi)
        
        # clear sign bit
        # [C] *(p+1)=*q&0X7FFF
        # (p is pointer to Lo, q is pointer to Hi)
        Lo = Rand._setShort1(Lo, Rand._getShort0(Hi) & 0x7FFF)
        
        # Hi bits 31-45->K
        # [C] k=*(q+1)<<1
        # [C] if (*q&0x8000) { k++ }
        # (q is pointer to Hi)
        k = Rand._getShort1(Hi) << 1
        if 0 != (Rand._getShort1(Hi) & 0x8000):
            k += 1
        
        # form Z + K [- M] (where Z=Lo): presubtract M to avoid overflow
        Lo -= Rand.M
        Lo += k
        if Lo < 0:
            Lo += Rand.M
        self._I = Lo
        
        # Lo x 1/(2**31-1)
        return (Lo * 4.656612875E-10)
    
    def uniform(self, a, b):
        """
        Generates a pseudo-random value from an uniform distribution.
        
        Parameters:
            a (double): The lower boundary, inclusive.
            b (double): The upper boundary, inclusive.
        
        Returns:
            The generated pseudo-random number.
        """
        
        if a > b:
            raise ValueError("For the normal pseudo-random generator, the lower boundary must not exceed the higher boundary")
        return (a + (b - a) * self.ranf())
    
    def random(self, i, n):
        """
        Generates a pseudo-random integer in a range from a uniform distribution.
        
        Parameters:
            i (int): The lower boundary, inclusive.
            n (int): The upper boundary, inclusive.
        
        Returns:
            The generated pseudo-random integer number.
        """
        
        if i > n:
            raise ValueError("For the normal pseudo-random generator, the lower boundary must not exceed the higher boundary")
        m = n - i
        d = int((m + 1.0) * self.ranf())
        return (i + d)
    
    def expntl(self, x):
        """
        Generates a pseudo-random value from an exponential distribution.
        
        Parameters:
            x (double): The mean value.
        
        Returns:
            The generated pseudo-random number.
        """
        
        return (-x * math.log(self.ranf()))
    
    def erlang(self, x, s):
        """
        Generates a pseudo-random value from an Erlang distribution.
        
        The standard deviation MUST NOT be larger than the mean.
        
        Parameters:
            x (double): The mean value.
            s (double): The standard deviation.
        
        Returns:
            The generated pseudo-random number.
        """
        
        if s > x:
            raise ValueError("For the Erlang pseudo-random generator, the standard deviation must not be larger than the mean value")
        
        z1 = x / s
        k = int(z1 * z1)
        z2 = 1.0
        for i in range(0, k):
            z2 *= self.ranf()
        return (-(x / k) * math.log(z2))
    
    def hyperx(self, x, s):
        """
        Generates a pseudo-random value from a Morse's two-stage hyperexponential distribution.
        
        The standard deviation MUST be larger than the mean.
        
        Parameters:
            x (double): The mean value.
            s (double): The standard deviation.
        
        Returns:
            The generated pseudo-random number.
        """
        
        if s <= x:
            raise ValueError("For the hyperexponential pseudo-random generator, the standard deviation must be larger than the mean value")
        
        cv = s / x
        z1 = cv * cv
        p = 0.5 * (1.0 - (math.sqrt((z1 - 1.0) / (z1 + 1.0))))
        if self.ranf() > p:
            z2 = (x / (1.0 - p))
        else:
            z2 = (x / p)
        return (-0.5 * z2 * math.log(self.ranf()))
    
    def normal(self, x, s):
        """
        Generates a pseudo-random value from a normal distribution.
        
        Parameters:
            x (double): The mean value.
            s (double): The standard deviation.
        
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
        return (x + z1 * s)
    
    def _setShort0(self, x, value):
        """
        Sets the least significant short of an integer.
        
        Parameters:
            x (int): The integer.
            value (int): The short.
        
        Returns:
            The integer with the least significant short replaced.
        """
        
        return (x & 0xFFFF0000) | (value & 0x0000FFFF)
    
    def _setShort1(self, x, value):
        """
        Sets the most significant short of an integer.
        
        Parameters:
            x (int): The integer.
            value (int): The short.
        
        Returns:
            The integer with the most significant short replaced.
        """
        
        return (x & 0x0000FFFF) | (((value) << 16) & 0xFFFF0000)
    
    def _getShort0(self, x):
        """
        Gets the least significant short of an integer.
        
        Parameters:
            x (int): The integer.
        
        Returns:
            The least significant short of the integer.
        """
        
        return (x & 0x0000FFFF)
    
    def _getShort1(self, x):
        """
        Gets the most significant short of an integer.
        
        Parameters:
            x (int): The integer.
        
        Returns:
            The most significant short of the integer.
        """
        
        return ((x >> 16) & 0x0000FFFF)

class EventDescriptor:
    """
    Data regarding a scheduled (for execution) or queued (in a facility) event in the 'smpl' simulation subsystem.
    """
    
    def __init__(self, blockNumber):
        """
        Creates an event descriptor.
        
        Parameters:
            blockNumber (int): The block number of the event descriptor.
        """
        
        self._blockNumber = blockNumber
        self.next = None
        self.eventCode = 0
        self.token = None
        self.remainingTimeToEvent = 0.0
        self.triggerTime = 0.0
        self.priority =0
    
    def __str__(self):
        return "EventDescriptor(" + self._blockNumber + ")"

class FacilityIdentifier:
    """
    Identifier of a facility (resource) in the 'smpl' simulation subsystem.
    
    In the original C version of 'smpl', facilities were identified by plain 'int' values.
    """
    
    def __init__(self, blockNumber):
        """
        Creates a facility identifier.
        
        Parameters:
            blockNumber (int): The initial block number of the facility.
        """
        
        self._blockNumber = blockNumber
    
    def __hash__(self):
        return self._blockNumber
    
    def __eq__(self, obj):
        if self is obj:
            result = True
        elif obj is None:
            result = False
        elif type(self) != type(obj):
            result = False
        else:
            result = (self._blockNumber == obj._blockNumber)
        return result
    
    def __str__(self):
        return "FacilityIdentifier(" + self._blockNumber + ")"

class FacilityData:
    """
    Data of a facility (resource) in the 'smpl' simulation subsystem.
    """
    
    def __init__(self, blockNumber, name, totalServers):
        """
        Creates an object which stores facility data.
        
        Parameters:
            blockNumber (int): The initial block number of the facility.
            name (string): The name of the facility.
            totalServers (int): The total amount of servers of the facility.
        """
        
        self._blockNumber = blockNumber
        
        self.name = name
        self.servers = [None] * totalServers
        for i in range(0, totalServers):
            self.servers[i] = FacilityServer(blockNumber + 2 + i)
        self.totalServers = totalServers
        self.busyServers = 0
        self.eventQueueLength = 0
        self.headEventDescriptor = None
        self.queueExitCount = 0
        self.preemptCount = 0
        self.timeOfLastChange = 0.0
        self.totalQueueingTime = 0.0
    
    def __str__(self):
        return "FacilityData(" + self._blockNumber + ")"

class FacilityServer:
    """
    An instance of a facility.
    """
    
    def __init__(self, blockNumber):
        """
        Creates a facility server.
        
        Parameters:
            blockNumber (int): The block number of the facility server.
        """
        
        self._blockNumber = blockNumber
        
        self.busyToken = None
        self.busyPriority = 0
        self.busyTime = 0.0
        self.releaseCount = 0
        self.totalBusyTime = 0.0
    
    def __str__(self):
        return "FacilityServer(" + self._blockNumber + ")"
