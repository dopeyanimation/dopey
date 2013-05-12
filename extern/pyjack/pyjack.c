/**
  * pyjackc - C module implementation for pyjack
  *
  * Copyright 2003 Andrew W. Schmeder <andy@a2hd.com>
  * Copyright 2010 Filipe Coelho (aka 'falkTX') <falktx@gmail.com>
  *
  * This source code is released under the terms of the GNU GPL v2.
  * See LICENSE for the full text of these terms.
  */

// Python includes
#include "Python.h"
#include "numpy/arrayobject.h"

// Jack
#include <jack/jack.h>
#include <jack/transport.h>

// C standard
#include <stdio.h>
#include <sys/time.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <unistd.h>
#include <fcntl.h>
#include <signal.h>

/*
TODO's:
- dettach on client on __del__
- free buffers
- close sockets
- hangup callback
- user python callbacks for non-rt events
- make global client a python object
- eventually deprecate the global client api
- remove the attach and detach methods
*/

// Global shared data for jack

/* Uncomment the next line if you have Jack2 */
#define JACK2 1


#define PYJACK_MAX_PORTS 256
#define W 0
#define R 1
typedef struct {
    PyObject_HEAD
    jack_client_t* pjc;                             // Client handle
    int            buffer_size;                     // Buffer size
    int            num_inputs;                      // Number of input ports registered
    int            num_outputs;                     // Number of output ports registered
    jack_port_t*   input_ports[PYJACK_MAX_PORTS];   // Input ports
    jack_port_t*   output_ports[PYJACK_MAX_PORTS];  // Output ports
    fd_set         input_rfd;                       // fdlist for select
    fd_set         output_rfd;                      // fdlist for select
    int            input_pipe[2];                   // socket pair for input port data
    int            output_pipe[2];                  // socket pair for output port data
    float*         input_buffer_0;                  // buffer used to transmit audio via slink...
    float*         output_buffer_0;                 // buffer used to send audio via slink...
    float*         input_buffer_1;                  // buffer used to transmit audio via slink...
    float*         output_buffer_1;                 // buffer used to send audio via slink...
    int            input_buffer_size;               // buffer_size * num_inputs * sizeof(sample_t)
    int            output_buffer_size;              // buffer_size * num_outputs * sizeof(sample_t)
    int            iosync;                          // true when the python side synchronizing properly...
    int            event_graph_ordering;            // true when a graph ordering event has occured
    int            event_port_registration;         // true when a port registration event has occured
    int            event_buffer_size;               // true when a buffer size change has occured
    int            event_sample_rate;               // true when a sample rate change has occured
    int            event_xrun;                      // true when a xrun occurs
    int            event_shutdown;                  // true when the jack server is shutdown
    int            event_hangup;                    // true when client got hangup signal
    int            active;                          // indicates if the client is currently process-enabled
} pyjack_client_t;

pyjack_client_t global_client;

pyjack_client_t * self_or_global_client(PyObject * self) {
    if (!self) return & global_client;
    return (pyjack_client_t*) self;
}

// Initialize global data
void pyjack_init(pyjack_client_t * client) {
    client->pjc = NULL;
    client->active = 0;
    client->iosync = 0;
    client->num_inputs = 0;
    client->num_outputs = 0;
    client->input_pipe[R] = 0;
    client->input_pipe[W] = 0;
    client->output_pipe[R] = 0;
    client->output_pipe[W] = 0;

    // Initialize unamed, raw datagram-type sockets...
    if (socketpair(PF_UNIX, SOCK_DGRAM, 0, client->input_pipe) == -1) {
        printf("ERROR: Failed to create socketpair input_pipe!!\n");
    }
    if (socketpair(PF_UNIX, SOCK_DGRAM, 0, client->output_pipe) == -1) {
        printf("ERROR: Failed to create socketpair output_pipe!!\n");
    }

    // Convention is that pipe[W=1] is the "write" end of the pipe, which is always non-blocking.
    fcntl(client->input_pipe[W], F_SETFL, O_NONBLOCK);
    fcntl(client->output_pipe[W], F_SETFL, O_NONBLOCK);
    fcntl(client->output_pipe[R], F_SETFL, O_NONBLOCK);

    // The read end, pipe[R=0], is blocking, but we use a select() call to make sure that data is really there.
    FD_ZERO(&client->input_rfd);
    FD_ZERO(&client->output_rfd);
    FD_SET(client->input_pipe[R], &client->input_rfd);
    FD_SET(client->output_pipe[R], &client->output_rfd);

    // Init buffers to null...
    client->input_buffer_size = 0;
    client->output_buffer_size = 0;
    client->input_buffer_0 = NULL;
    client->output_buffer_0 = NULL;
    client->input_buffer_1 = NULL;
    client->output_buffer_1 = NULL;
}

static void free_and_reset(float ** pointer)
{
    if (!*pointer) return;
    free(*pointer);
    *pointer=0;
}

static void close_and_reset(int * fd)
{
    if (!*fd) return;
    close(*fd);
    *fd=0;
}

// Finalize global data
void pyjack_final(pyjack_client_t * client) {
    client->pjc = NULL;
    // Free buffers...
    client->num_inputs = 0;
    client->num_outputs = 0;
    client->buffer_size = 0;
    free_and_reset(&client->input_buffer_0);
    free_and_reset(&client->input_buffer_1);
    free_and_reset(&client->output_buffer_0);
    free_and_reset(&client->output_buffer_1);
    // Close socket...
    close_and_reset(&client->input_pipe[R]);
    close_and_reset(&client->input_pipe[W]);
    close_and_reset(&client->output_pipe[R]);
    close_and_reset(&client->output_pipe[W]);
}

// (Re)initialize socketpair buffers
void init_pipe_buffers(pyjack_client_t  * client) {
    // allocate buffers for send and recv
    unsigned new_input_size = client->num_inputs * client->buffer_size * sizeof(float);
    if(client->input_buffer_size != new_input_size) {
        client->input_buffer_size = new_input_size;
        client->input_buffer_0 = realloc(client->input_buffer_0, new_input_size);
        client->input_buffer_1 = realloc(client->input_buffer_1, new_input_size);
        //printf("Input buffer size %d bytes\n", input_buffer_size);
    }
    unsigned new_output_size = client->num_outputs * client->buffer_size * sizeof(float);
    if(client->output_buffer_size != new_output_size) {
        client->output_buffer_size = new_output_size;
        client->output_buffer_0 = realloc(client->output_buffer_0, new_output_size);
        client->output_buffer_1 = realloc(client->output_buffer_1, new_output_size);
        //printf("Output buffer size %d bytes\n", output_buffer_size);
    }

    // set socket buffers to same size as snd/rcv buffers
    setsockopt(client->input_pipe[R], SOL_SOCKET, SO_RCVBUF, &client->input_buffer_size, sizeof(int));
    setsockopt(client->input_pipe[R], SOL_SOCKET, SO_SNDBUF, &client->input_buffer_size, sizeof(int));
    setsockopt(client->input_pipe[W], SOL_SOCKET, SO_RCVBUF, &client->input_buffer_size, sizeof(int));
    setsockopt(client->input_pipe[W], SOL_SOCKET, SO_SNDBUF, &client->input_buffer_size, sizeof(int));

    setsockopt(client->output_pipe[R], SOL_SOCKET, SO_RCVBUF, &client->output_buffer_size, sizeof(int));
    setsockopt(client->output_pipe[R], SOL_SOCKET, SO_SNDBUF, &client->output_buffer_size, sizeof(int));
    setsockopt(client->output_pipe[W], SOL_SOCKET, SO_RCVBUF, &client->output_buffer_size, sizeof(int));
    setsockopt(client->output_pipe[W], SOL_SOCKET, SO_SNDBUF, &client->output_buffer_size, sizeof(int));
}

// RT function called by jack
int pyjack_process(jack_nframes_t n, void* arg) {

    pyjack_client_t * client = (pyjack_client_t*) arg;
    int i, r;

    // Send input data to python side (non-blocking!)
    if (client->num_inputs) { 
        for(i = 0; i < client->num_inputs; i++) {
            memcpy(
                &client->input_buffer_0[client->buffer_size * i], 
                jack_port_get_buffer(client->input_ports[i], n), 
                (client->buffer_size * sizeof(float))
            );
        }

        r = write(client->input_pipe[W], client->input_buffer_0, client->input_buffer_size);

        if(r < 0) {
            client->iosync = 0;
        } else if(r == client->input_buffer_size) {
            client->iosync = 1;
        }
    }

    // Read data from python side (non-blocking!)
    if (client->num_outputs) {
        r = read(client->output_pipe[R], client->output_buffer_0, client->output_buffer_size);
        if(r != client->buffer_size * sizeof(float) * client->num_outputs) {
            //printf("not enough data; skipping output\n");
            return 0;
        }
        for(i = 0; i < client->num_outputs; i++) {
            memcpy(
                jack_port_get_buffer(client->output_ports[i], client->buffer_size), 
                client->output_buffer_0 + (client->buffer_size * i),
                client->buffer_size * sizeof(float)
            );
        }
    }

    return 0;
}

// Event notification of buffer size change
int pyjack_buffer_size_changed(jack_nframes_t n, void* arg) {
    pyjack_client_t * client = (pyjack_client_t*) arg;
    client->event_buffer_size = 1;
    return 0;
}

// Event notification of sample rate change
int pyjack_sample_rate_changed(jack_nframes_t n, void* arg) {
    pyjack_client_t * client = (pyjack_client_t*) arg;
    client->event_sample_rate = 1;
    return 0;
}

// Event notification of graph connect/disconnection
int pyjack_graph_order(void* arg) {
    pyjack_client_t * client = (pyjack_client_t*) arg;
    client->event_graph_ordering = 1;
    return 0;
}

// Event notification of xrun
int pyjack_xrun(void* arg) {
    pyjack_client_t * client = (pyjack_client_t*) arg;
    client->event_xrun = 1;
    return 0;
}

// Event notification of port registration or drop
void pyjack_port_registration(jack_port_id_t pid, int action, void* arg) {
    pyjack_client_t * client = (pyjack_client_t*) arg;
    client->event_port_registration = 1;
}

// Shutdown handler
void pyjack_shutdown(void * arg) {
    pyjack_client_t * client = (pyjack_client_t*) arg;
    client->event_shutdown = 1;
    client->pjc = NULL;    
}

// SIGHUP handler
void pyjack_hangup(int signal) {
    // TODO: what to do with non global clients
    global_client.event_hangup = 1;
    global_client.pjc = NULL;
}

// ------------- Python module stuff ---------------------

// Module exception object
static PyObject* JackError;
static PyObject* JackNotConnectedError;
static PyObject* JackUsageError;
static PyObject* JackInputSyncError;
static PyObject* JackOutputSyncError;

// Attempt to connect to the Jack server
static PyObject* attach(PyObject* self, PyObject* args)
{
    char* cname;
    if (! PyArg_ParseTuple(args, "s", &cname))
        return NULL;

    pyjack_client_t * client = self_or_global_client(self);
    if(client->pjc != NULL) {
        PyErr_SetString(JackUsageError, "A connection is already established.");
        return NULL;
    }

    jack_status_t status;
    client->pjc = jack_client_open(cname, JackNoStartServer, &status);
    if(client->pjc == NULL) {
        //TODO check status
        PyErr_SetString(JackNotConnectedError, "Failed to connect to Jack audio server.");
        return NULL;
    }

    jack_on_shutdown(client->pjc, pyjack_shutdown, client);
    signal(SIGHUP, pyjack_hangup); // TODO: This just works with global clients

    if(jack_set_process_callback(client->pjc, pyjack_process, client) != 0) {
        PyErr_SetString(JackError, "Failed to set jack process callback.");
        return NULL;
    }

    if(jack_set_buffer_size_callback(client->pjc, pyjack_buffer_size_changed, client) != 0) {
        PyErr_SetString(JackError, "Failed to set jack buffer size callback.");
        return NULL;
    }

    if(jack_set_sample_rate_callback(client->pjc, pyjack_sample_rate_changed, client) != 0) {
        PyErr_SetString(JackError, "Failed to set jack sample rate callback.");
        return NULL;
    }

    if(jack_set_port_registration_callback(client->pjc, pyjack_port_registration, client) != 0) {
        PyErr_SetString(JackError, "Failed to set jack port registration callback.");
        return NULL;
    }

    if(jack_set_graph_order_callback(client->pjc, pyjack_graph_order, client) != 0) {
        PyErr_SetString(JackError, "Failed to set jack graph order callback.");
        return NULL;
    }

    if(jack_set_xrun_callback(client->pjc, pyjack_xrun, client) != 0) {
        PyErr_SetString(JackError, "Failed to set jack xrun callback.");
        return NULL;
    }

    // Get buffer size
    client->buffer_size = jack_get_buffer_size(client->pjc);

    // Success!
    Py_INCREF(Py_None);
    return Py_None;
}

// Detach client from the jack server (also destroys all connections)
static PyObject* detach(PyObject* self, PyObject* args)
{
    pyjack_client_t * client = self_or_global_client(self);

    if(client->pjc != NULL) {
        jack_client_close(client->pjc);
        pyjack_final(client);
    }

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject* unregister_port(PyObject* self, PyObject* args)
{
    pyjack_client_t * client = self_or_global_client(self);
    char* port_name;
    if (! PyArg_ParseTuple(args, "s", &port_name))
        return NULL;

    if(client->pjc == NULL) {
        PyErr_SetString(JackNotConnectedError, "Jack connection has not yet been established.");
        return NULL;
    }

//     if(client->active) {
//         PyErr_SetString(JackUsageError, "Cannot unregister ports while client is active.");
//         return NULL;
//     }

    int i = 0;
    for (i=0;i<client->num_inputs;i++) {
        if (strcmp(port_name, jack_port_short_name(client->input_ports[i]))) continue;
        int error = jack_port_unregister(client->pjc, client->input_ports[i]);
        if (error) {
            PyErr_SetString(JackError, "Unable to unregister input port.");
            return NULL;
        }
        client->num_inputs--;
        for (;i<client->num_inputs;i++) {
            client->input_ports[i] = client->input_ports[i+1];
        }
        init_pipe_buffers(client);
        Py_INCREF(Py_None);
        return Py_None;
    }

    for (i=0;i<client->num_outputs;i++) {
        if (strcmp(port_name, jack_port_short_name(client->output_ports[i]))) continue;
        int error = jack_port_unregister(client->pjc, client->output_ports[i]);
        if (error) {
            PyErr_SetString(JackError, "Unable to unregister output port.");
            return NULL;
        }
        client->num_outputs--;
        for (;i<client->num_outputs;i++) {
            client->output_ports[i] = client->output_ports[i+1];
        }
        init_pipe_buffers(client);
        Py_INCREF(Py_None);
        return Py_None;
    }
    PyErr_SetString(JackUsageError, "Port not found.");
    return NULL;
}


// Create a new port for this client
// Unregistration of ports is not supported; you must disconnect, reconnect, re-reg all ports instead.
static PyObject* register_port(PyObject* self, PyObject* args)
{
    pyjack_client_t * client = self_or_global_client(self);

    int flags;
    char* pname;
    if (! PyArg_ParseTuple(args, "si", &pname, &flags))
        return NULL;

    if(client->pjc == NULL) {
        PyErr_SetString(JackNotConnectedError, "Jack connection has not yet been established.");
        return NULL;
    }

//     if(client->active) {
//         PyErr_SetString(JackUsageError, "Cannot register ports while client is active.");
//         return NULL;
//     }

    if(client->num_inputs >= PYJACK_MAX_PORTS) {
        PyErr_SetString(JackUsageError, "Cannot create more than 256 ports. Sorry.");
        return NULL;
    }

    jack_port_t* jp = jack_port_register(client->pjc, pname, JACK_DEFAULT_AUDIO_TYPE, flags, 0);
    if(jp == NULL) {
        PyErr_SetString(JackError, "Failed to create port.");
        return NULL;
    }

    // Store pointer to this port and increment counter
    if(flags & JackPortIsInput) {
        client->input_ports[client->num_inputs] = jp;
        client->num_inputs++;
    }
    if(flags & JackPortIsOutput) {
        client->output_ports[client->num_outputs] = jp;
        client->num_outputs++;
    }

    init_pipe_buffers(client);
    Py_INCREF(Py_None);
    return Py_None;
}

// Returns a list of all port names registered in the Jack system
static PyObject* get_ports(PyObject* self, PyObject* args)
{
    PyObject* plist;
    const char** jplist;
    int i;

    pyjack_client_t * client = self_or_global_client(self);
    if(client->pjc == NULL) {
        PyErr_SetString(JackNotConnectedError, "Jack connection has not yet been established.");
        return NULL;
    }

    jplist = jack_get_ports(client->pjc, NULL, NULL, 0);

    i = 0;
    plist = PyList_New(0);
    if(jplist != NULL) {
        while(jplist[i] != NULL) {
            PyList_Append(plist, Py_BuildValue("s", jplist[i]));
            //free(jplist[i]);  // Memory leak or not??
            i++;
        }
    }

    Py_INCREF(plist);
    return plist;
}

// Return port flags (an integer)
static PyObject* get_port_flags(PyObject* self, PyObject* args)
{
    char* pname;
    jack_port_t* jp;
    int i;

    pyjack_client_t * client = self_or_global_client(self);
    if(client->pjc == NULL) {
        PyErr_SetString(JackNotConnectedError, "Jack connection has not yet been established.");
        return NULL;
    }

    if (! PyArg_ParseTuple(args, "s", &pname))
        return NULL;

    jp = jack_port_by_name(client->pjc, pname);
    if(jp == NULL) {
        PyErr_SetString(JackError, "Bad port name.");
        return NULL;
    }

    i = jack_port_flags(jp);
    if(i < 0) {
        PyErr_SetString(JackError, "Error getting port flags.");
        return NULL;
    }

    return Py_BuildValue("i", i);
}

// Return a list of full port names connected to the named port
// Port does not need to be owned by this client.
static PyObject* get_connections(PyObject* self, PyObject* args)
{
    char* pname;
    const char** jplist;
    jack_port_t* jp;
    PyObject* plist;
    int i;

    pyjack_client_t * client = self_or_global_client(self);
    if(client->pjc == NULL) {
        PyErr_SetString(JackNotConnectedError, "Jack connection has not yet been established.");
        return NULL;
    }

    if (! PyArg_ParseTuple(args, "s", &pname))
        return NULL;

    jp = jack_port_by_name(client->pjc, pname);
    if(jp == NULL) {
        PyErr_SetString(JackError, "Bad port name.");
        return NULL;
    }

    jplist = jack_port_get_all_connections(client->pjc, jp);

    i = 0;
    plist = PyList_New(0);
    if(jplist != NULL) {
        while(jplist[i] != NULL) {
            PyList_Append(plist, Py_BuildValue("s", jplist[i]));
            //free(jplist[i]);  // memory leak or not?
            i++;
        }
    }

    Py_INCREF(plist);
    return plist;
}

// connect_port
static PyObject* port_connect(PyObject* self, PyObject* args)
{
    char* src_name;
    char* dst_name;

    pyjack_client_t * client = self_or_global_client(self);
    if(client->pjc == NULL) {
        PyErr_SetString(JackNotConnectedError, "Jack connection has not yet been established.");
        return NULL;
    }

    if (! PyArg_ParseTuple(args, "ss", &src_name, &dst_name))
        return NULL;

    jack_port_t * src = jack_port_by_name(client->pjc, src_name);
    if (!src) {
        PyErr_SetString(JackUsageError, "Non existing source port.");
        return NULL;
        }
    jack_port_t * dst = jack_port_by_name(client->pjc, dst_name);
    if (!dst) {
        PyErr_SetString(JackUsageError, "Non existing destination port.");
        return NULL;
        }
    if(! client->active) {
        if(jack_port_is_mine(client->pjc, src) || jack_port_is_mine(client->pjc, dst)) {
            PyErr_SetString(JackUsageError, "Jack client must be activated to connect own ports.");
            return NULL;
        }
    }
    int error = jack_connect(client->pjc, src_name, dst_name);
    if (error !=0 && error != EEXIST) {
        PyErr_SetString(JackError, "Failed to connect ports.");
        return NULL;
    }

    Py_INCREF(Py_None);
    return Py_None;
}

static int jack_port_connected_to_extern(const pyjack_client_t * client, 
                                         const jack_port_t * src, 
                                         const char* dst_name)
{
    // finds connections of src, then checks if dst is in there
    const char ** existing_connections = jack_port_get_all_connections(client->pjc, src);
    if (existing_connections) {
        int i; // non C99 nonsense
        for (i = 0; existing_connections[i]; i++) {
            if (strcmp(existing_connections[i], dst_name) == 0)
                return 1;
        }
    }
    return 0;
}

// disconnect_port
static PyObject* port_disconnect(PyObject* self, PyObject* args)
{
    char* src_name;
    char* dst_name;
    pyjack_client_t * client = self_or_global_client(self);

    if(client->pjc == NULL) {
        PyErr_SetString(JackNotConnectedError, "Jack connection has not yet been established.");
        return NULL;
    }

    if (! PyArg_ParseTuple(args, "ss", &src_name, &dst_name))
        return NULL;

    jack_port_t * src = jack_port_by_name(client->pjc, src_name);
    if (!src) {
        PyErr_SetString(JackUsageError, "Non existing source port.");
        return NULL;
    }

    jack_port_t * dst = jack_port_by_name(client->pjc, dst_name);
    if (!dst) {
        PyErr_SetString(JackUsageError, "Non existing destination port.");
        return NULL;
    }

    if(jack_port_connected_to_extern(client, src, dst_name)) {
        if (jack_disconnect(client->pjc, src_name, dst_name)) {
            PyErr_SetString(JackError, "Failed to disconnect ports.");
            return NULL;
        }
    }

    Py_INCREF(Py_None);
    return Py_None;
}

// get_buffer_size
static PyObject* get_buffer_size(PyObject* self, PyObject* args)
{
    pyjack_client_t * client = self_or_global_client(self);

    if(client->pjc == NULL) {
        PyErr_SetString(JackNotConnectedError, "Jack connection has not yet been established.");
        return NULL;
    }

    int bs = jack_get_buffer_size(client->pjc);
    return Py_BuildValue("i", bs);
}

// get_sample_rate
static PyObject* get_sample_rate(PyObject* self, PyObject* args)
{
    pyjack_client_t * client = self_or_global_client(self);
    if(client->pjc == NULL) {
        PyErr_SetString(JackNotConnectedError, "Jack connection has not yet been established.");
        return NULL;
    }

    int sr = jack_get_sample_rate(client->pjc);
    return Py_BuildValue("i", sr);
}

// activate
static PyObject* activate(PyObject* self, PyObject* args)
{
    pyjack_client_t * client = self_or_global_client(self);
    if(client->pjc == NULL) {
        PyErr_SetString(JackNotConnectedError, "Jack connection has not yet been established.");
        return NULL;
    }

    if(client->active) {
        PyErr_SetString(JackUsageError, "Client is already active.");
        return NULL;
    }

    if(jack_activate(client->pjc) != 0) {
        PyErr_SetString(JackUsageError, "Could not activate client.");
        return NULL;
    }

    client->active = 1;
    Py_INCREF(Py_None);
    return Py_None;
}

// deactivate
static PyObject* deactivate(PyObject* self, PyObject* args)
{
    pyjack_client_t * client = self_or_global_client(self);
    if(client->pjc == NULL) {
        PyErr_SetString(JackNotConnectedError, "Jack connection has not yet been established.");
        return NULL;
    }

    if(! client->active) {
        PyErr_SetString(JackUsageError, "Client is not active.");
        return NULL;
    }

    if(jack_deactivate(client->pjc) != 0) {
        PyErr_SetString(JackError, "Could not deactivate client.");
        return NULL;
    }

    client->active = 0;
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject * get_client_name(PyObject* self, PyObject* args)
{
    pyjack_client_t * client = self_or_global_client(self);
    if(client->pjc == NULL) {
        PyErr_SetString(JackNotConnectedError, "Jack connection has not yet been established.");
        return NULL;
    }
    return Py_BuildValue("s", jack_get_client_name(client->pjc));
}

/** Commit a chunk of audio for the outgoing stream, if any.
  * Return the next chunk of audio from the incoming stream, if any
  */
static PyObject* process(PyObject* self, PyObject *args)
{
    int j, c, r;
    PyArrayObject *input_array;
    PyArrayObject *output_array;

    pyjack_client_t * client = self_or_global_client(self);
    if(! client->active) {
        PyErr_SetString(JackUsageError, "Client is not active.");
        return NULL;
    }

    // Import the first and only arg...
    if (! PyArg_ParseTuple(args, "O!O!", &PyArray_Type, &output_array, &PyArray_Type, &input_array))
        return NULL;

    if(input_array->descr->type_num != PyArray_FLOAT || output_array->descr->type_num != PyArray_FLOAT) {
        PyErr_SetString(PyExc_ValueError, "arrays must be of type float");
        return NULL;
    }
    if(input_array->nd != 2 || output_array->nd != 2) {
        printf("%d, %d\n", input_array->nd, output_array->nd);
        PyErr_SetString(PyExc_ValueError, "arrays must be two dimensional");
        return NULL;
    }
    if((client->num_inputs > 0 && input_array->dimensions[1] != client->buffer_size) || 
       (client->num_outputs > 0 && output_array->dimensions[1] != client->buffer_size)) {
        PyErr_SetString(PyExc_ValueError, "columns of arrays must match buffer size.");
        return NULL;
    }
    if(client->num_inputs > 0 && input_array->dimensions[0] != client->num_inputs) {
        PyErr_SetString(PyExc_ValueError, "rows for input array must match number of input ports");
        return NULL;
    }
    if(client->num_outputs > 0 && output_array->dimensions[0] != client->num_outputs) {
        PyErr_SetString(PyExc_ValueError, "rows for output array must match number of output ports");
        return NULL;
    }

    // Get input data
    // If we are out of sync, there might be bad data in the buffer
    // So we have to throw that away first...
    if (client->input_buffer_size) {
        r = read(client->input_pipe[R], client->input_buffer_1, client->input_buffer_size);

        // Copy data into array...
        for(c = 0; c < client->num_inputs; c++) {
            for(j = 0; j < client->buffer_size; j++) {
                memcpy(
                    input_array->data + (c*input_array->strides[0] + j*input_array->strides[1]), 
                    client->input_buffer_1 + j + (c*client->buffer_size), 
                    sizeof(float)
                );
            }
        }

        if(!client->iosync) {
            PyErr_SetString(JackInputSyncError, "Input data stream is not synchronized.");
            return NULL;
        }
    }

    if (client->output_buffer_size) {
        // Copy output data into output buffer...
        for(c = 0; c < client->num_outputs; c++) {
            for(j = 0; j < client->buffer_size; j++) {
                memcpy(&client->output_buffer_1[j + (c*client->buffer_size)],
                       output_array->data + c*output_array->strides[0] + j*output_array->strides[1],
                       sizeof(float)
                );
            }
        }

        // Send... raise an exception if the output data stream is full.
        r = write(client->output_pipe[W], client->output_buffer_1, client->output_buffer_size);

        if(r != client->output_buffer_size) {
            PyErr_SetString(JackOutputSyncError, "Failed to write output data.");
            return NULL;
        }
    }

    // Okay...    
    Py_INCREF(Py_None);
    return Py_None;
}

// Return event status numbers...
static PyObject* check_events(PyObject* self, PyObject *args)
{
    pyjack_client_t * client = self_or_global_client(self);

    PyObject* d;
    d = PyDict_New();
    if(d == NULL) return NULL;

    PyDict_SetItemString(d, "graph_ordering", Py_BuildValue("i", client->event_graph_ordering));
    PyDict_SetItemString(d, "port_registration", Py_BuildValue("i", client->event_port_registration));
    PyDict_SetItemString(d, "xrun", Py_BuildValue("i", client->event_xrun));
    PyDict_SetItemString(d, "shutdown", Py_BuildValue("i", client->event_shutdown));
    PyDict_SetItemString(d, "hangup", Py_BuildValue("i", client->event_hangup));

    // Reset all
    client->event_graph_ordering = 0;
    client->event_port_registration = 0;
    client->event_xrun = 0;
    client->event_shutdown = 0;
    client->event_hangup = 0;

    return d;
}

static PyObject* get_frame_time(PyObject* self, PyObject* args)
{
    pyjack_client_t * client = self_or_global_client(self);
    if(client->pjc == NULL) {
        PyErr_SetString(JackNotConnectedError, "Jack connection has not yet been established.");
        return NULL;
    }

    int frt = jack_frame_time(client->pjc);
    return Py_BuildValue("i", frt);
}

static PyObject* get_current_transport_frame(PyObject* self, PyObject* args)
{
    pyjack_client_t * client = self_or_global_client(self);
    if(client->pjc == NULL) {
        PyErr_SetString(JackNotConnectedError, "Jack connection has not yet been established.");
        return NULL;
    }

    int ftr = jack_get_current_transport_frame(client->pjc);
    return Py_BuildValue("i", ftr);
}

static PyObject* transport_locate (PyObject* self, PyObject* args)
{
    pyjack_client_t * client = self_or_global_client(self);
    jack_nframes_t newfr;

    if (! PyArg_ParseTuple(args, "i", &newfr))
        return NULL;

    if(client->pjc == NULL) {
        PyErr_SetString(JackNotConnectedError, "Jack connection has not yet been established.");
        return NULL;
    }

    jack_transport_locate (client->pjc,newfr);
    return Py_None;
}

static PyObject* get_transport_state (PyObject* self, PyObject* args)
{
    //int state;
    pyjack_client_t * client = self_or_global_client(self);
    if(client->pjc == NULL) {
        PyErr_SetString(JackNotConnectedError, "Jack connection has not yet been established.");
        return NULL;
    }

    jack_transport_state_t transport_state;
    transport_state = jack_transport_query (client->pjc, NULL);

    return Py_BuildValue("i", transport_state);
}

#ifdef JACK2
static PyObject* get_version(PyObject* self, PyObject* args)
{
    int major, minor, micro, proto;
    jack_get_version(&major, &minor, &micro, &proto);
    return Py_BuildValue("iiii", major, minor, micro, proto);
}
#endif

#ifdef JACK2
static PyObject* get_version_string(PyObject* self, PyObject* args)
{
    const char* version;
    version = jack_get_version_string();
    return Py_BuildValue("s", version);
}
#endif

static PyObject* get_cpu_load(PyObject* self, PyObject* args)
{
    pyjack_client_t * client = self_or_global_client(self);
    if(client->pjc == NULL) {
        PyErr_SetString(JackNotConnectedError, "Jack connection has not yet been established.");
        return NULL;
    }

    float cpu_load = jack_cpu_load(client->pjc);

    return Py_BuildValue("f", cpu_load);
}

static PyObject* get_port_short_name(PyObject* self, PyObject* args)
{
    char * port_name;

    if (! PyArg_ParseTuple(args, "s", &port_name))
        return NULL;

    if (port_name == NULL) {
        PyErr_SetString(JackError, "Port name cannot be empty.");
        return NULL;
    }

    pyjack_client_t * client = self_or_global_client(self);
    if(client->pjc == NULL) {
        PyErr_SetString(JackNotConnectedError, "Jack connection has not yet been established.");
        return NULL;
    }

    jack_port_t * port = jack_port_by_name(client->pjc, port_name);
    if (!port) {
        PyErr_SetString(JackError, "Port name cannot be empty.");
        return NULL;
    }
    const char * port_short_name = jack_port_short_name(port);

    return Py_BuildValue("s", port_short_name);
}

static PyObject* get_port_type(PyObject* self, PyObject* args)
{
    char * port_name;

    if (! PyArg_ParseTuple(args, "s", &port_name))
        return NULL;

    if (port_name == NULL) {
        PyErr_SetString(JackError, "Port name cannot be empty.");
        return NULL;
    }

    pyjack_client_t * client = self_or_global_client(self);
    if(client->pjc == NULL) {
        PyErr_SetString(JackNotConnectedError, "Jack connection has not yet been established.");
        return NULL;
    }

    jack_port_t * port = jack_port_by_name(client->pjc, port_name);
    if (!port) {
        PyErr_SetString(JackError, "Port name cannot be empty.");
        return NULL;
    }
    const char * port_type = jack_port_type(port);

    return Py_BuildValue("s", port_type);
}

#ifdef JACK2
static PyObject* get_port_type_id(PyObject* self, PyObject* args)
{
    char * port_name;

    if (! PyArg_ParseTuple(args, "s", &port_name))
        return NULL;

    if (port_name == NULL) {
        PyErr_SetString(JackError, "Port name cannot be empty.");
        return NULL;
    }

    pyjack_client_t * client = self_or_global_client(self);
    if(client->pjc == NULL) {
        PyErr_SetString(JackNotConnectedError, "Jack connection has not yet been established.");
        return NULL;
    }

    jack_port_t * port = jack_port_by_name(client->pjc, port_name);
    if (!port) {
        PyErr_SetString(JackError, "Port name cannot be empty.");
        return NULL;
    }

    jack_port_type_id_t port_type_id = jack_port_type_id(port);

    int ret = port_type_id;
    return Py_BuildValue("i", ret);
}
#endif

static PyObject* is_realtime(PyObject* self, PyObject* args)
{
    pyjack_client_t * client = self_or_global_client(self);
    if(client->pjc == NULL) {
        PyErr_SetString(JackNotConnectedError, "Jack connection has not yet been established.");
        return NULL;
    }

    int realtime = jack_is_realtime(client->pjc);
    return Py_BuildValue("i", realtime);
}

static PyObject* port_is_mine(PyObject* self, PyObject* args)
{
    char * port_name;

    if (! PyArg_ParseTuple(args, "s", &port_name))
        return NULL;

    if (port_name == NULL) {
        PyErr_SetString(JackError, "Port name cannot be empty.");
        return NULL;
    }

    pyjack_client_t * client = self_or_global_client(self);
    if(client->pjc == NULL) {
        PyErr_SetString(JackNotConnectedError, "Jack connection has not yet been established.");
        return NULL;
    }

    jack_port_t * port = jack_port_by_name(client->pjc, port_name);
    if (!port) {
        PyErr_SetString(JackError, "Port name cannot be empty.");
        return NULL;
    }

    int port_mine = jack_port_is_mine(client->pjc, port);
    return Py_BuildValue("i", port_mine);
}


static PyObject* transport_stop (PyObject* self, PyObject* args)
{
    pyjack_client_t * client = self_or_global_client(self);
    if(client->pjc == NULL) {
        PyErr_SetString(JackNotConnectedError, "Jack connection has not yet been established.");
        return NULL;
    }

    jack_transport_stop (client->pjc);

    return Py_None;
}

static PyObject* transport_start (PyObject* self, PyObject* args)
{
    pyjack_client_t * client = self_or_global_client(self);
    if(client->pjc == NULL) {
        PyErr_SetString(JackNotConnectedError, "Jack connection has not yet been established.");
        return NULL;
    }

    jack_transport_start (client->pjc);

    return Py_None;
}

static PyObject* set_buffer_size(PyObject* self, PyObject* args)
{
    int size;

    if (! PyArg_ParseTuple(args, "i", &size))
        return NULL;

    pyjack_client_t * client = self_or_global_client(self);
    if(client->pjc == NULL) {
        PyErr_SetString(JackNotConnectedError, "Jack connection has not yet been established.");
        return NULL;
    }

    jack_nframes_t nsize = size;
    jack_set_buffer_size(client->pjc, nsize);

    return Py_None;
}

static PyObject* set_sync_timeout(PyObject* self, PyObject* args)
{
    int time;

    if (! PyArg_ParseTuple(args, "i", &time))
        return NULL;

    pyjack_client_t * client = self_or_global_client(self);
    if(client->pjc == NULL) {
        PyErr_SetString(JackNotConnectedError, "Jack connection has not yet been established.");
        return NULL;
    }

    jack_time_t timeout = time;
    jack_set_sync_timeout(client->pjc, timeout);

    return Py_None;
}


// Python Module definition ---------------------------------------------------

static PyMethodDef pyjack_methods[] = {
  {"attach",             attach,                  METH_VARARGS, "attach(name):\n  Attach client to the Jack server"},
  {"detach",             detach,                  METH_VARARGS, "detach():\n  Detach client from the Jack server"},
  {"activate",           activate,                METH_VARARGS, "activate():\n  Activate audio processing"},
  {"deactivate",         deactivate,              METH_VARARGS, "deactivate():\n  Deactivate audio processing"},
  {"connect",            port_connect,            METH_VARARGS, "connect(source, destination):\n  Connect two ports, given by name"},
  {"disconnect",         port_disconnect,         METH_VARARGS, "disconnect(source, destination):\n  Disconnect two ports, given by name"},
  {"process",            process,                 METH_VARARGS, "process(output_array, input_array):\n  Exchange I/O data with RT Jack thread"},
  {"get_client_name",    get_client_name,         METH_VARARGS, "client_name():\n  Returns the actual name of the client"},
  {"register_port",      register_port,           METH_VARARGS, "register_port(name, flags):\n  Register a new port for this client"},
  {"unregister_port",    unregister_port,         METH_VARARGS, "unregister_port(name):\n  Unregister an existing port for this client"},
  {"get_ports",          get_ports,               METH_VARARGS, "get_ports():\n  Get a list of all ports in the Jack graph"},
  {"get_port_flags",     get_port_flags,          METH_VARARGS, "get_port_flags(port):\n  Return flags of a port (flags are bits in an integer)"},
  {"get_connections",    get_connections,         METH_VARARGS, "get_connections():\n  Get a list of all ports connected to a port"},
  {"get_buffer_size",    get_buffer_size,         METH_VARARGS, "get_buffer_size():\n  Get the buffer size currently in use"},
  {"get_sample_rate",    get_sample_rate,         METH_VARARGS, "get_sample_rate():\n  Get the sample rate currently in use"},
  {"check_events",       check_events,            METH_VARARGS, "check_events():\n  Check for event notifications"},
  {"get_frame_time",     get_frame_time,          METH_VARARGS, "get_frame_time():\n  Returns the current frame time"},
  {"get_current_transport_frame", get_current_transport_frame,  METH_VARARGS, "get_current_transport_frame():\n  Returns the current transport frame"},
  {"transport_locate",   transport_locate,        METH_VARARGS, "transport_locate(frame):\n  Sets the current transport frame"},
  {"get_transport_state",get_transport_state,     METH_VARARGS, "get_transport_state():\n  Returns the current transport state"},
  {"transport_stop",     transport_stop,          METH_VARARGS, "transport_stop():\n  Stopping transport"},
  {"transport_start",    transport_start,         METH_VARARGS, "transport_start():\n  Starting transport"},
#ifdef JACK2
  {"get_version",        get_version,             METH_VARARGS, "get_version():\n  Returns the version of JACK, in form of several numbers"},
  {"get_version_string", get_version_string,      METH_VARARGS, "get_version_string():\n  Returns the version of JACK, in form of a string"},
#endif
  {"get_cpu_load",       get_cpu_load,            METH_VARARGS, "get_cpu_load():\n  Returns the current CPU load estimated by JACK"},
  {"get_port_short_name",get_port_short_name,     METH_VARARGS, "get_port_short_name(port):\n  Returns the short name of the port (not including the \"client_name:\" prefix)"},
  {"get_port_type",      get_port_type,           METH_VARARGS, "get_port_type(port):\n  Returns the port type (in a string)"},
#ifdef JACK2
  {"get_port_type_id",   get_port_type_id,        METH_VARARGS, "get_port_type_id(port):\n  Returns the port type id"},
#endif
  {"is_realtime",        is_realtime,             METH_VARARGS, "is_realtime():\n  Returns 1 if the JACK subsystem is running with -R (--realtime)"},
  {"port_is_mine",       port_is_mine,            METH_VARARGS, "port_is_mine(port):\n  Returns 1 if port belongs to the running client"},
  {"set_buffer_size",    set_buffer_size,         METH_VARARGS, "set_buffer_size(size):\n  Sets Jack Buffer Size (minimum appears to be 16)."},
  {"set_sync_timeout",   set_sync_timeout,        METH_VARARGS, "set_sync_timeout(time):\n  Sets the delay (in microseconds) before the timeout expires."},
  {NULL, NULL}
};

static PyObject *
Client_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    pyjack_client_t *self = (pyjack_client_t *)type->tp_alloc(type, 0);
    if (self == NULL) return NULL;

    pyjack_init(self);

    return (PyObject *)self;
}

static int
Client_init(PyObject *self, PyObject *args, PyObject *kwds)
{	
    int status = 0;
    if (!attach(self, args)) status = -1;
    return status;
}

static void
Client_dealloc(PyObject* self)
{
puts("pyjack: dealloc");
    detach(self, Py_None);
    self->ob_type->tp_free(self);
}


static PyTypeObject pyjack_ClientType = {
    PyObject_HEAD_INIT(NULL)
    /*ob_size*/             0, 
    /*tp_name*/             "jack.Client",
    /*tp_basicsize*/        sizeof(pyjack_client_t),
    /*tp_itemsize*/         0,
    /*tp_dealloc*/          Client_dealloc,
    /*tp_print*/            0,
    /*tp_getattr*/          0,
    /*tp_setattr*/          0,
    /*tp_compare*/          0,
    /*tp_repr*/             0,
    /*tp_as_number*/        0,
    /*tp_as_sequence*/      0,
    /*tp_as_mapping*/       0,
    /*tp_hash */            0,
    /*tp_call*/             0,
    /*tp_str*/              0,
    /*tp_getattro*/         0,
    /*tp_setattro*/         0,
    /*tp_as_buffer*/        0,
    /*tp_flags*/            Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
    /* tp_doc */            "JACK client object.\n"
                            "Instatiate a jack.Client to interact with a jack server.\n"
                            ,
    /* tp_traverse */       0,
    /* tp_clear */          0,
    /* tp_richcompare */    0,
    /* tp_weaklistoffset */ 0,
    /* tp_iter */           0,
    /* tp_iternext */       0,
    /* tp_methods */        pyjack_methods,
    /* tp_members */        0,
    /* tp_getset */         0,
    /* tp_base */           0,
    /* tp_dict */           0,
    /* tp_descr_get */      0,
    /* tp_descr_set */      0,
    /* tp_dictoffset */     0,
    /* tp_init */           Client_init,
    /* tp_alloc */          0,
    /* tp_new */            Client_new,
};



#ifndef PyMODINIT_FUNC  /* declarations for DLL import/export */
#define PyMODINIT_FUNC void
#endif
PyMODINIT_FUNC
initjack(void)
{
  PyObject *m, *d;

  if (PyType_Ready(&pyjack_ClientType) < 0)
    return;
  m = Py_InitModule3("jack", pyjack_methods,
	"This module provides bindings to manage clients for the Jack Audio Connection Kit architecture");
  if (m == NULL)
    goto fail;
  d = PyModule_GetDict(m);
  if (d == NULL)
    goto fail;

  Py_INCREF(&pyjack_ClientType);
  PyModule_AddObject(m, "Client", (PyObject *)&pyjack_ClientType);

// Jack errors 
  JackError = PyErr_NewException("jack.Error", NULL, NULL);
  JackNotConnectedError = PyErr_NewException("jack.NotConnectedError", NULL, NULL);
  JackUsageError = PyErr_NewException("jack.UsageError", NULL, NULL);
  JackInputSyncError = PyErr_NewException("jack.InputSyncError", NULL, NULL);
  JackOutputSyncError = PyErr_NewException("jack.OutputSyncError", NULL, NULL);

  PyDict_SetItemString(d, "Error", JackError);
  PyDict_SetItemString(d, "NotConnectedError", JackNotConnectedError);
  PyDict_SetItemString(d, "UsageError", JackUsageError);
  PyDict_SetItemString(d, "InputSyncError", JackInputSyncError);
  PyDict_SetItemString(d, "OutputSyncError", JackOutputSyncError);
// Jack flags
  PyDict_SetItemString(d, "IsInput", Py_BuildValue("i", JackPortIsInput));
  PyDict_SetItemString(d, "IsOutput", Py_BuildValue("i", JackPortIsOutput));
  PyDict_SetItemString(d, "IsTerminal", Py_BuildValue("i", JackPortIsTerminal));
  PyDict_SetItemString(d, "IsPhysical", Py_BuildValue("i", JackPortIsPhysical));
  PyDict_SetItemString(d, "CanMonitor", Py_BuildValue("i", JackPortCanMonitor));
  PyDict_SetItemString(d, "TransportStopped", Py_BuildValue("i", JackTransportStopped));
  PyDict_SetItemString(d, "TransportRolling", Py_BuildValue("i", JackTransportRolling));
  PyDict_SetItemString(d, "TransportStarting", Py_BuildValue("i", JackTransportStarting));

  // Enable Numeric module
  import_array();

  if (PyErr_Occurred())
    goto fail;

  // Init jack data structures
  pyjack_init(&global_client);

  return;

fail:
  Py_FatalError("Failed to initialize module pyjack");
}
