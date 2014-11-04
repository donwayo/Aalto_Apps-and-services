# Peer-to-Peer Network
T-110.5150 - Applications and Services in Internet

## Requirements
* Python 2.7
* PyQt4

## Running the program
We provide both a command line client, and a GUI client. The command line client is only available on *nix platoforms though. 

Both clients accept a single optional command line argument that specifies the port that the P2P Client should run on. 

Execute the GUI client with:
```$ python gui.py [port] ```

or run the command line client like this:

```$ python main.py [port]```

## GUI Client
The GUI client presents an easy to use interface that allows you to search for keys on the network, join hosts, send bye messages, and monitor the status of peer connections and received query messages. 

## Command line client
The following commands can be used to interact with the command line client:

### j:Join
The join command takes as an argument the host it should connect to. The host should be `ip[:port]` where the `port` is optional or instead just a `b` to indicate the default bootstrap node.

#### Examples:
Join host 10.0.0.1 on port 10334:
```
j10.0.0.1:10334
- 04:06:44 PM: Joined successfully @ 10.0.0.1:10334
```

Join host 10.0.0.1 on default port:
```
j10.0.0.1
- 04:06:44 PM: Joined successfully @ 10.0.0.1:10001
```

Join bootstrap node:
```
jb
Joining bootstrap node.
- 04:06:36 PM: Joined successfully @ 130.233.43.41:10001
```

### s:Search
The search commands takes a single argument: the key to search for in the P2P network. 

#### Example
```
stestKey
- 03:51:31 PM: Result from: 130.233.43.41
- 03:51:31 PM: ID: 1 - Value: 17846608
```

### i:Information
Prints information about the currently connected peers, and the query messages received. 

#### Example
```
i
Query messages:
    4002904148  130.233.43.41:10001 (3.47588896751s)
    525168851   130.233.43.41:10001 (20.8143548965s)
    1989850708  130.233.43.41:10001 (14.6517219543s)
    3914749117  130.233.43.41:10001 (9.68740105629s)

Peer connections: 4
0   130.233.43.41:10001 Peer connected.
    Alive for 25.7578291893
1   10.0.0.3:10001  Attempting connection.
    Waiting for TCP handshake.
2   127.0.0.1:10001 Peer connected.
    Alive for 2.26246500015
3   127.0.0.1:49531 Peer connected.
    Alive for 2.26304602623
```

### b:Bye
Sends a bye message to a specific host. This command takes as a parameter the index of the host. This index can be retrieved from the information screen.

#### Example
```
b5
Sending Bye message to connection 5
```

### l:Loglevel
Change the loglevel of the program. This can be an integer value between 1-5, and will set the log level correspondingly. The higher the level, the less information that is shown.

Useful levels:
* 5-3: print only necessary information for the interaction with the program.
* 2: print information about the workings of the program, plus the previous levels.
* 1: print detailed information about messages sent, plus the previous levels.

#### Example
```
l3
Changed loglvl to 30
```

### q:Quit
Quits the command line client and sends Bye messages to all the connected peers.
#### Example
```
q
Bye
```
