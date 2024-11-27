<p align="center">
  <a href="" rel="noopener">
 <img width=200px height=200px src="./.github/assets/deeds.svg" alt="Bot logo"></a>
</p>

<h3 align="center">DEEDs</h3>

<div align="center">

![Static Badge](https://img.shields.io/badge/status-draft-8A2BE2?style=flat-square)
![GitHub License](https://img.shields.io/github/license/nitheesh-me/DEEDs?style=flat-square)

</div>

---

🤖 Distributed Encrypted Ephemeral Data Storage System (based on GFS)

## 📝 Table of Contents

- [📝 Table of Contents](#-table-of-contents)
- [🧐 About ](#-about-)
- [🎥 Demo / Working ](#-demo--working-)
- [💭 How it works ](#-how-it-works-)
- [🎈 Usage ](#-usage-)
- [🏁 Getting Started ](#-getting-started-)
  - [Prerequisites](#prerequisites)
  - [Installing](#installing)
- [🚀 Deploying on your own ](#-deploying-on-your-own-)
- [⛏️ Built Using ](#️-built-using-)
- [✍️ Authors ](#️-authors-)
- [🎉 Acknowledgements ](#-acknowledgements-)
- [TODO](#todo)

## 🧐 About <a name = "about"></a>

DEEDs is a distributed encrypted ephemeral data storage system based on the Google File System (GFS). It is designed to store data in a distributed manner, encrypt it and then delete it after a certain period of time.

## 🎥 Demo / Working <a name = "demo"></a>

TODO: Add demo
<!-- ![Working]() -->

## 💭 How it works <a name = "working"></a>

TODO: Add implementation details

## 🎈 Usage <a name = "usage"></a>

TODO: Add usage instructions with examples

Verify if and where the DEEDs filesystem is mounted:
```bash
mount | grep DEEDSFS
```

## 🏁 Getting Started <a name = "getting_started"></a>

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See [deployment](#deployment) for notes on how to deploy the project on a live system.

### Prerequisites

What things you need to install the software and how to install them.

```
TODO: Add prerequisites
```

### Installing

TODO: Add installation instructions

<!-- A step by step series of examples that tell you how to get a development env running.

Say what the step will be

```
Give the example
```

And repeat

```
until finished
```

End with an example of getting some data out of the system or using it for a little demo. -->

## 🚀 Deploying on your own <a name = "deployment"></a>

```
docker compose up --build --remove-orphans --watch
```

## ⛏️ Built Using <a name = "built_using"></a>

TODO: Add technologies used

## ✍️ Authors <a name = "authors"></a>

TODO: Add authors

## 🎉 Acknowledgements <a name = "acknowledgement"></a>

<!-- - Hat tip to anyone whose code was used -->
- Inspiration
- References

<!--
fusepy
https://github.com/Gan-Tu/cppGFS2.0/tree/master/examples
-->

## TODO

```mermaid
sequenceDiagram
    participant Client as Client
    participant GFS_Master as GFS Master
    participant Secondary_Master as Secondary GFS Master
    participant ChunkServer as ChunkServer
    participant Replica1 as ChunkServer Replica 1
    participant Replica2 as ChunkServer Replica 2
    participant Network as Network
    participant WAL as Write-Ahead Log
    participant Cache as Client Cache

    %% Client request for a file
    Client->>GFS_Master: Request(fileName)
    GFS_Master->>GFS_Master: Check metadata for fileName
    GFS_Master->>Client: Return chunk locations (chunk1, chunk2, chunk3)

    %% Client requests chunk data
    Client->>ChunkServer: Request(chunk1)
    ChunkServer->>Network: Send chunk1 data
    Network->>Client: Deliver chunk1 data

    Client->>ChunkServer: Request(chunk2)
    ChunkServer->>Network: Send chunk2 data
    Network->>Client: Deliver chunk2 data

    Client->>ChunkServer: Request(chunk3)
    ChunkServer->>Network: Send chunk3 data
    Network->>Client: Deliver chunk3 data

    %% Chunkserver failure scenario (high availability)
    ChunkServer->>Network: Failure detected (chunkserver down)
    GFS_Master->>ChunkServer: Reassign chunks to healthy servers
    GFS_Master->>Replica1: Notify replica for chunk1 reassignment
    GFS_Master->>Replica2: Notify replica for chunk2 reassignment
    Replica1->>Network: Retrieve chunk1 data
    Replica2->>Network: Retrieve chunk2 data
    Client->>Replica1: Request(chunk1)  %% Failover process
    Replica1->>Network: Send chunk1 data
    Network->>Client: Deliver chunk1 data
    Client->>Replica2: Request(chunk2)
    Replica2->>Network: Send chunk2 data
    Network->>Client: Deliver chunk2 data

    %% GFS Master failover process
    GFS_Master->>GFS_Master: Detect failure (Master down)
    Secondary_Master->>GFS_Master: Assume primary master role
    Secondary_Master->>Client: Reassign chunk locations for ongoing requests
    Secondary_Master->>ChunkServer: Reassign chunks and metadata updates
    ChunkServer->>Secondary_Master: Acknowledge reassignment
    Client->>Secondary_Master: Continue file access via secondary master

    %% Lease Management during Writes
    Client->>GFS_Master: Request to write (fileName, chunk data)
    GFS_Master->>WAL: Log write operation (write-ahead log)
    WAL->>GFS_Master: Confirm log entry
    GFS_Master->>GFS_Master: Allocate chunk locations
    GFS_Master->>ChunkServer: Assign chunk locations
    ChunkServer->>Client: Acknowledge chunk write success
    Client->>Replica1: Replicate chunk data
    Client->>Replica2: Replicate chunk data
    Replica1->>ChunkServer: Receive replicated chunk data
    Replica2->>ChunkServer: Receive replicated chunk data
    GFS_Master->>ChunkServer: Confirm replication success
    WAL->>GFS_Master: Mark write operation as complete

    %% Periodic heartbeat and failure detection
    ChunkServer->>GFS_Master: Heartbeat (status)
    GFS_Master->>ChunkServer: Acknowledge heartbeat
    ChunkServer->>GFS_Master: Failure (reassignment)

    %% Client-side Caching and Cache Invalidations
    Client->>Cache: Retrieve cached chunk1 data
    Cache->>ChunkServer: Check if chunk is still valid
    ChunkServer->>Cache: Invalidate stale data if chunk reassigned
    Cache->>Client: Return fresh chunk1 data

    %% Periodic checkpoint and garbage collection
    GFS_Master->>ChunkServer: Request checkpoint
    ChunkServer->>GFS_Master: Send checkpoint data
    GFS_Master->>ChunkServer: Confirm checkpoint success
    GFS_Master->>ChunkServer: Delete unused chunk data (GC)

    %% Concurrency Control and Append Operations
    Client->>GFS_Master: Request to append data (fileName, chunk data)
    GFS_Master->>ChunkServer: Allocate chunk for append operation
    ChunkServer->>GFS_Master: Acknowledge chunk allocation
    Client->>ChunkServer: Append data to chunk
    ChunkServer->>GFS_Master: Update metadata with appended data
    GFS_Master->>Client: Confirm append success

    %% Chunk Creation during Writes (Splitting Large Files)
    Client->>GFS_Master: Request to write large file
    GFS_Master->>GFS_Master: Split file into multiple chunks (chunk1, chunk2, chunk3)
    GFS_Master->>ChunkServer: Allocate chunk locations for large file
    ChunkServer->>Client: Acknowledge chunk allocation and begin write
    Client->>ChunkServer: Write chunk1 data
    ChunkServer->>GFS_Master: Confirm chunk1 write
    Client->>ChunkServer: Write chunk2 data
    ChunkServer->>GFS_Master: Confirm chunk2 write
    Client->>ChunkServer: Write chunk3 data
    ChunkServer->>GFS_Master: Confirm chunk3 write
    GFS_Master->>Client: Acknowledge full file write completion

    %% Stale Data Removal (Garbage Collection)
    GFS_Master->>ChunkServer: Detect unused chunks
    ChunkServer->>GFS_Master: Mark chunks for garbage collection
    GFS_Master->>ChunkServer: Delete orphaned chunks (stale data)
    ChunkServer->>GFS_Master: Confirm chunk deletion
```