# Overview
A Python implementation of the discrete event simulation environment 'smpl'. The original 'smpl' library was developed by Myron H. MacDougall. This version is mostly based on the C implementation of the library, which was released on October 22, 1987. This version is also based on the C version with bugfixes provided by Elias Procópio Duarte Júnior, and on the C version provided by Teemu Kerola.

# Basic usage

The code snippets in this document use the following symbols (which should be imported from library): `Smpl`, `RESERVED`, and `QUEUED`. In order to import them, use the following line:

```
from simulation_smpl import Smpl, RESERVED, QUEUED
```

The SMPL library allows applications to implement discrete event simulations. A simulation takes place around a _simulation object_, which is an instance of the `Smpl` class. In order to create a simulation object, simply use the class constructor, which does not take any arguments.

```
smpl = Smpl()
```

The simulation object may not be used right away, and must be initialized. Initialization is done by invoking the `init` method, which takes a single argument - the simulation name. The simulation name is a mandatory argument, but is is used only for debugging. After this method is invoked, the simulation object becomes ready to use. The `init` method also clears all previous settings and statistics, allowing a simulation object to be reused between simulations.

```
smpl.init('my simulation')
```

The simulations built around the 'Smpl' library doe not use real time, but simulated time: a year may pass in the simulation during a split second of real time. The simulated time is measured in 'time units', which may translate to actual units - such as seconds, minutes or hours - based on the simulation requirements. When the simulation begins, the time is `0.0` (zero), and it moves forward as the simulation runs. To check the current simulated time, use the `time` method of the simulation object.

```
print('the simulated time is %d time units' % (smpl.time(),))
```

A discrete event simulation is based on discrete events. A discreve event is something that happens in the simulated environment in a single moment in simulated time. Events will not take place in the simulated environment in unless the simulation program schedules them. Scheduling is the process of setting up an event that will happen on a certain simulated time. Scheduling must happen before the simulation begins, and may happen during the simulation. In order to schedule an event, use the `schedule` method of the simulation object. This method takes three arguments: a number which identifies the type of the event (called 'event code' or 'event type'), the amount of simulated time units until the event is triggered (called 'time to event'), and a value which represents the event target (called 'event token'). The event token must not be `None`. The following snippet schedules an event whose type is `MY_EVENT_TYPE` with a dummy target, which will take place 1 time unit after the current simulated time.

```
MY_EVENT_TYPE = 1
smpl.schedule(MY_EVENT_TYPE, 1.0, "")
```

Scheduling events does not run the simulation. In order to run the simulation, the `cause` method of the simulation object must be invoked repeatedly. This method advances the simulated time to the time of the next event, removes it from the list of scheduled events, and returns a tuple with the event code and the event token. If there are no more events, this method returns `None`.
```
event_code, token = smpl.cause()
```

The following sample code runs a simulation in which a custom event is triggered each 1 time unit. The simulation ends after the simulated time gets past 10 time units.

```
MY_EVENT_TYPE = 1

smpl = Smpl()
smpl.init('my simulation')

smpl.schedule(MY_EVENT_TYPE, 1.0, "")

print('the simulation will begin\n')

while True:
  event_code, token = smpl.cause()
  if smpl.time() > 10.0:
    break
  print('an event with code %i has been triggered at time %f\n' % (event_code, smpl.time()))
  if event_code == MY_EVENT_TYPE:
    smpl.schedule(MY_EVENT_TYPE, 1.0, "")

print('the simulation has ended\n')
```

# Multiple processes and shared resources

In real environments, usually there are resources which may not be used concurrently by multiple processes. These are called 'shared resources', and their access is usually managed using semaphores. The 'Smpl' library can be used to simulate shared resources. In the library, a set of shared resources with a semaphore is called a 'facility', and each individual resource is called a 'facility server'.

Facilities are usually created created before the simulation begins. The original C version of `Smpl` enforces that facilites are created beforehand (trying to create a facility during the simulation causes a crash), but this version (by design) does not. In order to create a facility, use the `facility` method of the simulation object. It takes two arguments - the facility name and the number of servers -, and returns a 'facility identifier', which is a value that uniquely identifies the facility in the simulation. For all purposes the facility identifier should be treated like an opaque value. The code snippet below creates a facility called 'resource name' with 2 servers.

```
fac = smpl.facility('resource name', 2)
```

Usually, in order to simulate multiple processes, each process is represented by a handle.A handle may be a value of any kind, and they are usually declared as constants before the simulation begins.

```
PROCESS_1 = 1
```

During the simulation, processes may try to take ownership of a resource. This is done by calling the `request` method of the simulation object. This method takes three arguments - the facility identifier, the token (which represents the process), and the priority (higher values indicate higher priority) -, and returns a value indicating whether the ownership was taken - `RESERVED` means that the process got ownership of the resource, and `QUEUED` means it has not. If the `request` method returns `QUEUED`, the last event is scheduled to happen again once the resource is available for the process. If there are multple processess waiting on the facility, the one with the largest priority will have precedence over the others. The code snippet below tries to take ownership of the facility `fac` for the process `PROCESS_1` with zero (default) priority.

```
result = smpl.request(fac, PROCESS_1, 0)
```

After a process is done with the shared resource, it must release the facility. This is done by calling the `release` method of the simulation object. This method takes two arguments - the facility identifier and the token. The code snippet below releases the ownership over the facility `fac`.

```
smpl.release(fac, PROCESS_1)
```
