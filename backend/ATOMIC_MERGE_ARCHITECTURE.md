# Atomic Face Cluster Merge - Architecture Diagrams

## Sequence Diagram: Successful Merge

```mermaid
sequenceDiagram
    actor Client
    participant Service as FaceService
    participant DB as PostgreSQL
    participant VS as Qdrant
    participant Repo as Repository

    Client->>Service: merge_clusters([A, B], C)

    Note over Service: Phase 1: Collect Updates
    Service->>Repo: find_cluster_by_id(C)
    Repo-->>Service: target_cluster
    Service->>Repo: find_cluster_by_id(A)
    Repo-->>Service: source_cluster_A
    Service->>Repo: find_cluster_by_id(B)
    Repo-->>Service: source_cluster_B
    Service->>Repo: find_faces_by_ids([faces from A, B])
    Repo-->>Service: faces with original_cluster_ids

    Note over Service: Phase 2: Update Database (Transactional)
    Service->>Service: face.assign_to_cluster(target_cluster_id)
    Service->>Repo: save_faces_batch([faces])
    Repo->>DB: BEGIN TRANSACTION
    DB->>DB: UPDATE faces SET cluster_id = C
    DB->>DB: COMMIT
    DB-->>Repo: success
    Repo-->>Service: saved

    Note over Service: Phase 3: Batch Update Vector Store
    Service->>Service: prepare vector_updates list
    Service->>VS: update_face_payloads_batch([(face_id_1, {cluster_id: C}), ...])
    VS->>VS: set_payload(collection=faces, payload={cluster_id: C}, points=[...])
    VS-->>Service: success

    Note over Service: Phase 4: Cleanup
    Service->>Repo: delete_cluster(A)
    DB->>DB: DELETE FROM face_clusters WHERE id = A
    DB-->>Repo: success
    Service->>Repo: delete_cluster(B)
    DB->>DB: DELETE FROM face_clusters WHERE id = B
    DB-->>Repo: success

    Service-->>Client: target_cluster (merged)
```

## Sequence Diagram: Merge with Vector Store Failure & Compensation

```mermaid
sequenceDiagram
    actor Client
    participant Service as FaceService
    participant DB as PostgreSQL
    participant VS as Qdrant Vector Store
    participant Repo as Repository

    Client->>Service: merge_clusters([A, B], C)

    Note over Service: Phase 1: Collect Updates
    Service->>Repo: find_cluster_by_id(C)
    Repo-->>Service: target_cluster
    Service->>Repo: find_cluster_by_id(A)
    Repo-->>Service: source_cluster_A
    Service->>Repo: find_faces_by_ids([faces])
    Repo-->>Service: faces with original_cluster_ids<br/>(stored: face_1→A, face_2→A, face_3→B)

    Note over Service: Phase 2: Update Database
    Service->>Repo: save_faces_batch([faces])
    Repo->>DB: BEGIN TRANSACTION
    DB->>DB: UPDATE faces SET cluster_id = C
    DB->>DB: COMMIT
    DB-->>Repo: success ✓

    Note over Service: Phase 3: Batch Update Vector Store
    Service->>VS: update_face_payloads_batch([(face_1, {cluster_id: C}), ...])
    VS->>VS: set_payload(collection=faces, payload={cluster_id: C}, points=[...])
    VS-->>Service: EXCEPTION: "Vector store unavailable" ✗

    alt EXCEPTION CAUGHT
        Note over Service: Phase 4a: Compensation - Revert Database
        Service->>Service: Revert all faces to original cluster IDs<br/>face_1.cluster_id = A<br/>face_2.cluster_id = A<br/>face_3.cluster_id = B

        Service->>Repo: save_faces_batch([faces])
        Repo->>DB: BEGIN TRANSACTION
        DB->>DB: UPDATE faces SET cluster_id = [original]
        DB->>DB: COMMIT
        DB-->>Repo: success ✓

        Note over Service: Phase 4b: Revert Vector Store
        Service->>VS: update_face_payloads_batch([(face_1, {cluster_id: A}), ...])
        VS->>VS: set_payload(collection=faces, payload={cluster_id: A}, points=[...])
        VS-->>Service: success ✓

        Service->>Service: logger.critical("Manual intervention may be required")
        Service-->>Client: EXCEPTION: Original vector store error
    end
```

## State Diagram: Merge Operation States

```mermaid
stateDiagram-v2
    [*] --> Phase1Collect

    Phase1Collect --> Phase1Collect: Iterate source clusters
    Phase1Collect --> Phase2DB: Updates collected<br/>(no state changes)

    Phase2DB --> Phase2DB_Txn: All faces prepared<br/>in memory
    Phase2DB_Txn --> Phase2DB_Commit: Transaction commits<br/>DB updated ✓
    Phase2DB_Commit --> Phase3VectorStore: Database consistent

    Phase2DB --> Rollback_DB_Fail: Transaction fails<br/>DB unchanged
    Rollback_DB_Fail --> [*]: Merge aborted<br/>Safe state

    Phase3VectorStore --> Phase3VectorStore: Batch update prepared
    Phase3VectorStore --> Phase4Cleanup: Batch succeeds<br/>Vector store updated ✓
    Phase4Cleanup --> DeleteSourceClusters: Success verified
    DeleteSourceClusters --> [*]: Merge complete ✓

    Phase3VectorStore --> Phase4Compensate: Batch fails<br/>Vector store error ✗
    Phase4Compensate --> Phase4Compensate_DB: Revert DB faces
    Phase4Compensate_DB --> Phase4Compensate_VS: Revert vector store
    Phase4Compensate_VS --> Phase4Log_Critical: Compensation complete
    Phase4Log_Critical --> [*]: Inconsistency prevented ✓<br/>Manual review needed

    Phase4Compensate --> Phase4Compensate_Fail: Compensation fails<br/>Unrecoverable ✗
    Phase4Compensate_Fail --> Phase4Log_Critical_Fail: Log CRITICAL error
    Phase4Log_Critical_Fail --> [*]: MANUAL INTERVENTION<br/>REQUIRED ✗✗

    style Phase1Collect fill:#e1f5ff
    style Phase2DB fill:#c8e6c9
    style Phase3VectorStore fill:#fff9c4
    style Phase4Cleanup fill:#c8e6c9
    style Phase4Compensate fill:#ffccbc
    style Phase4Compensate_Fail fill:#ffcdd2
    style Phase4Log_Critical_Fail fill:#ffcdd2
```

## Data Flow: Normal Merge (100 Faces)

```mermaid
graph TD
    A["Client requests merge<br/>merge_clusters<br/>source_ids=[A, B]<br/>target_id=C"]

    A --> B["Phase 1: Collect<br/>Get target cluster C<br/>Get source clusters A, B<br/>Find 100 faces total<br/>Track original cluster IDs"]

    B --> C["In-Memory State<br/>all_face_updates = [<br/>  Face1, cluster_A<br/>  Face2, cluster_A<br/>  ...<br/>  Face100, cluster_B<br/>]"]

    C --> D["Phase 2: Database<br/>PostgreSQL Transaction<br/>Batch update all 100 faces<br/>SET cluster_id = C<br/>COMMIT"]

    D --> E["Database State<br/>✓ All 100 faces<br/>  cluster_id = C<br/>✓ Transaction committed"]

    E --> F["Phase 3: Vector Store<br/>Qdrant Batch Update<br/>set_payload with 100 point IDs<br/>payload = cluster_id: C"]

    F --> G["Vector Store State<br/>✓ All 100 faces<br/>  payload.cluster_id = C"]

    G --> H["Phase 4: Cleanup<br/>Delete cluster A<br/>Delete cluster B<br/>Save target cluster C"]

    H --> I["Final State<br/>✓ Source clusters deleted<br/>✓ 100 faces in target<br/>✓ DB and VS consistent"]

    I --> J["Client Response<br/>Merged cluster C<br/>Contains 100 faces"]

    style A fill:#e3f2fd
    style B fill:#c8e6c9
    style C fill:#fff9c4
    style D fill:#c8e6c9
    style E fill:#c8e6c9
    style F fill:#fff9c4
    style G fill:#c8e6c9
    style H fill:#c8e6c9
    style I fill:#c8e6c9
    style J fill:#e3f2fd
```

## Data Flow: Merge with Failure & Compensation

```mermaid
graph TD
    A["Client requests merge<br/>source_ids=[A, B]<br/>target_id=C"]

    A --> B["Phase 1-2: Success<br/>Faces collected<br/>Database updated"]

    B --> C["Phase 3: Vector Store Update<br/>Batch update to Qdrant<br/>update_face_payloads_batch<br/>..."]

    C --> D{"Qdrant Response"}

    D -->|Success| E["Phase 4: Cleanup<br/>Delete source clusters<br/>SUCCESS ✓"]

    D -->|FAILURE| F["Phase 4a: Compensation<br/>Revert Database<br/>for each face:<br/>  cluster_id = original"]

    F --> G["Phase 4b: Revert Vector<br/>update_face_payloads_batch<br/>Restore original cluster_ids"]

    G --> H{"Revert Success?"}

    H -->|Yes| I["All Changes Reverted ✓<br/>DB consistent<br/>VS consistent<br/>Log ERROR + context"]

    H -->|No| J["CRITICAL FAILURE ✗<br/>DB and VS inconsistent<br/>Log CRITICAL error<br/>Manual intervention needed"]

    E --> K["Success Result<br/>Merged cluster C"]
    I --> K["Partial Success<br/>Merge rolled back<br/>Original state restored"]
    J --> L["UNRECOVERABLE<br/>Require Manual Fix"]

    K --> M["Response to Client"]
    L --> M

    style A fill:#e3f2fd
    style B fill:#c8e6c9
    style C fill:#fff9c4
    style D fill:#fff9c4
    style E fill:#c8e6c9
    style F fill:#ffccbc
    style G fill:#ffccbc
    style H fill:#ffccbc
    style I fill:#ffccbc
    style J fill:#ffcdd2
    style K fill:#c8e6c9
    style L fill:#ffcdd2
    style M fill:#e3f2fd
```

## Architecture: Multi-Store Consistency Pattern

```mermaid
graph TB
    subgraph "Application Layer"
        Service["FaceService<br/>merge_clusters()"]
        Logger["Structured Logger<br/>INFO, ERROR, CRITICAL"]
    end

    subgraph "Phase 1: Collection"
        P1["Collect Updates<br/>No state changes"]
    end

    subgraph "Phase 2: Database Update"
        P2A["Prepare faces<br/>in memory"]
        P2B["PostgreSQL<br/>Transaction"]
        P2C["Commit all faces<br/>atomically"]
    end

    subgraph "Phase 3: Vector Update"
        P3A["Prepare vector updates<br/>batch list"]
        P3B["Qdrant batch update<br/>set_payload"]
        P3C{Success?}
    end

    subgraph "Phase 4: Cleanup/Compensation"
        P4A["Delete source<br/>clusters"]
        P4B["Revert database<br/>faces"]
        P4C["Revert vector store<br/>payloads"]
        P4D["Log CRITICAL<br/>requires manual fix"]
    end

    subgraph "Data Stores"
        DB["PostgreSQL<br/>faces table<br/>face_clusters table"]
        VS["Qdrant<br/>face_embeddings<br/>collection"]
    end

    Service --> P1
    P1 --> P2A
    P2A --> P2B
    P2B --> P2C
    P2C --> DB
    P2C --> P3A
    P3A --> P3B
    P3B --> VS
    P3B --> P3C
    P3C -->|Success| P4A
    P4A --> DB
    P3C -->|Failure| P4B
    P4B --> DB
    P4C --> VS
    P4D --> Logger
    Logger -.->|Monitor| Service

    style Service fill:#e3f2fd
    style P1 fill:#c8e6c9
    style P2A fill:#c8e6c9
    style P2B fill:#c8e6c9
    style P2C fill:#c8e6c9
    style P3A fill:#fff9c4
    style P3B fill:#fff9c4
    style P3C fill:#fff9c4
    style P4A fill:#c8e6c9
    style P4B fill:#ffccbc
    style P4C fill:#ffccbc
    style P4D fill:#ffcdd2
    style DB fill:#b3e5fc
    style VS fill:#b3e5fc
```

## Comparison: Race Condition vs Atomic Update

```mermaid
graph LR
    subgraph Before["BEFORE: Race Condition"]
        B1["merge_clusters()"]
        B2["Loop each face:<br/>UPDATE db<br/>UPDATE vector store"]
        B3["After 2 faces:<br/>Vector store fails"]
        B4["RESULT:<br/>DB: All faces in C<br/>VS: Face1,2 in C<br/>   Face3 in B<br/>INCONSISTENT!"]
    end

    subgraph After["AFTER: Atomic Merge"]
        A1["merge_clusters()"]
        A2["Phase 1: Collect all<br/>Phase 2: Batch DB<br/>Phase 3: Batch VS"]
        A3["Vector store fails"]
        A4["RESULT:<br/>DB: All faces in B<br/>VS: All faces in B<br/>CONSISTENT!<br/>+ Retry available"]
    end

    Before -.->|Problem| A1
    B1 --> B2
    B2 --> B3
    B3 --> B4
    A1 --> A2
    A2 --> A3
    A3 --> A4

    style B4 fill:#ffcdd2
    style A4 fill:#c8e6c9
```

## Failure Recovery Paths

```mermaid
graph TD
    Start["merge_clusters()<br/>START"]

    Start --> Phase1["Phase 1: Collect<br/>No state changes"]
    Phase1 --> Phase2["Phase 2: Update DB<br/>Transactional"]

    Phase2 --> DBFail{DB Transaction<br/>fails?}
    DBFail -->|Yes| Fail1["SAFE: Roll back<br/>No changes applied<br/>Retry immediately"]
    DBFail -->|No| Phase3

    Phase3["Phase 3: Update<br/>Vector Store<br/>Batch operation"]
    Phase3 --> VSFail{Batch update<br/>fails?}

    VSFail -->|No| Phase4["Phase 4: Cleanup<br/>Delete source clusters<br/>SUCCESS ✓"]
    Phase4 --> Success["Return merged cluster<br/>All consistent"]

    VSFail -->|Yes| Comp1["Compensation:<br/>Revert database"]
    Comp1 --> Comp2["Revert vector store<br/>payloads"]
    Comp2 --> CompSuccess{Both<br/>reverted?}

    CompSuccess -->|Yes| PartialSuccess["Partial Success ✓<br/>Merge rolled back<br/>Return error"]
    CompSuccess -->|No| ManualFix["CRITICAL FAILURE ✗<br/>Manual intervention<br/>required<br/>Log all details"]

    Fail1 --> End["Return error<br/>Retry available"]
    Success --> End
    PartialSuccess --> End
    ManualFix --> AdminNeeded["Administrator<br/>must verify both stores<br/>and sync manually"]

    style Start fill:#e3f2fd
    style Phase1 fill:#c8e6c9
    style Phase2 fill:#c8e6c9
    style Phase3 fill:#fff9c4
    style Phase4 fill:#c8e6c9
    style Success fill:#c8e6c9
    style Fail1 fill:#c8e6c9
    style Comp1 fill:#ffccbc
    style Comp2 fill:#ffccbc
    style PartialSuccess fill:#ffccbc
    style ManualFix fill:#ffcdd2
    style AdminNeeded fill:#ffcdd2
    style End fill:#e3f2fd
```
