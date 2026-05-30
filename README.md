# P2D (Paper-to-Digital) Document Processing & Compliance Automation Pipeline

An end-to-end automated pipeline designed to digitize, parse, map, validate, and synchronize physical/paper-based document flows into an enterprise digital infrastructure. This project handles the complete lifecycle of pulling encrypted data, executing complex metadata extraction using AI/LLM structured schemas, formatting records into secure regulatory compliant API payloads, and systematically cataloging the final processing results.

## 🚀 Process Architecture & Pipeline Breakdown

The workflow is modularized into 12 discrete parts managed via a master orchestration loop to ensure strict synchronization, verification, and automated error handling across system boundaries.


---

### 📂 Detailed Phase & Script Directory

#### Phase 1: Backend Extraction & Asset Retrieval (Parts 1 - 3)
* **`P2Dpart1.py` (XML Manifest Ingestion):** Parses standard hierarchical XML metadata files inside the document staging area. It locates targeted directory nodes (e.g., `Upload Paper Here`), extracts specific operational manifest pairs (`Key` and `Description`), and compiles them into a clean tracking index column layout in an Excel workbook.
* **`P2Dpart2.py` (Secure S3 File Downloader):** Reads the unique `Key` values generated in Phase 1 and runs an internal shell wrapper script (`./bin/S3Encrypter.sh`) with strict rate-limiting connection padding (1-second intervals) to sequentially grab raw backend XML data batches securely.
* **`P2dpart3.py` (Base64 Decoder & Asset Reconstitution):** Decodes raw transactional XML content wrappers by targeting the embedded byte stream element (`<Document64>`). It decodes the stream back into physical binaries, natively outputting original multi-format attachments (`.pdf`, `.png`, `.jpg`) into the active processing workspace.

#### Phase 2: Orchestration & Infrastructure Routing (Part 4)
* **`P2Dpart4.py` (Document Relocation API Client):** Handles server-side administrative document movement. It queries custom migration endpoints (`/document/v2/movedoc`) using secure local credentials, shifting verified items out of initial input queues into final file paths mapped out via operational tracking columns (`Target folder`).

#### Phase 3: Testing Enclaves & Endpoint Handshakes (Parts 5 - 7)
* **`P2Dpart5.py` (Transaction History PUT Client):** A standalone module used to explicitly validate network connections and test target JSON payloads or structural layouts targeting the raw Transaction History platform (`/transactionhistory/v1/putthhistorypaper`).
* **`P2Dpart6.py` (Artifact PUT Client):** A testbed component designed to load, test-read, and transmit custom compliance structural bodies (`ArtifactBody.xml`) via explicit API streams directed to active compliance gateways (`/artifact/v1/put`).
* **`P2Dpart7.py` (Transaction Exchange PUT Client):** A network validation helper script focused on transmitting structured multi-tenant payload frames straight into high-throughput ingestion clusters (`/transactionhistory/v1/puttexchange`).

#### Phase 4: Dynamic XML Ingestion & Transaction Assembly Engine (Parts 8 - 10)
* **`P2Dpart8.py` (Transaction History Payload Assembler):** Reads structured text documents parsed by generative models, cleans timestamp variations into standard `ISO 8601` formats (`YYYY-MM-DDTHH:MM:SS.mmmZ`), and maps itemized data points (NDCs, Lot numbers, Expirations) into unified transaction structures (`urn:tracelink:transactionhistory`).
* **`P2Dpart9.py` (Transaction Exchange Schema Mapper):** Normalizes messy source entity titles using a 5-tier tiered lookup system evaluated directly against enterprise mapping records (`Alternative Names.xlsx`). It generates target recipient definitions (`shipToLocation`) and exports them inside clean informational transaction payload blocks.
* **`P2Dpart10.py` (Compliance Artifact Base64 Packager):** Re-encodes processed multi-page PDFs directly into custom machine-readable wrapper files. It binds individual artifacts seamlessly to their parent transaction histories by embedding explicit identifiers (`ArtifactID`, `LastChange` tracking metrics).

#### Phase 5: Master Orchestration & Bulk Reconciliation Loop (Parts 11 - 12)
* **`P2Dpart11.py` (Core End-to-End Orchestrator):** The centralized pipeline controller. It processes incoming JSON/text extractions from directory inputs, tracks conditional null validations, dynamically executes Phase 4 data assemblers sequentially, manages session authentication boundaries, and pushes live transaction calls downstream across every API endpoint while logging process states.
* **`P2Dpart12.py` (Bulk Excel Status Reconciliation):** Scans the workflow directory for complete operational execution state texts, reads localized output strings, extracts critical transaction values, maps them back to initial inventory catalogs, and runs an index-based spreadsheet patch engine using `openpyxl` to seamlessly update macro trackers.

---

## 🛠️ Technical Specifications & Dependencies

* **Language Runtime:** Python 3.8+
* **Core File & IO Frameworks:** `pandas`, `openpyxl` (Structured tracking matrices)
* **API/Networking Layer:** `requests`, `urllib3` (Secure internal communication loops)
* **Markup/Validation Components:** `lxml` and `xml.etree.ElementTree` (Schema compiling)
* **Internal Core Modules:** `json`, `base64`, `re`, `uuid`, `shutil`, `secrets`, `datetime`, `logging`

---

## 📂 Repository File System Structure

```placeholders
├── P2Dpart1.py             # XML extraction & initial manifest logging
├── P2Dpart2.py             # Rate-limited shell secure downloader (S3 wrapper)
├── P2dpart3.py             # Base64 decoder & native asset re-builder
├── P2Dpart4.py             # Server routing endpoint integration (File Movement)
├── P2Dpart5.py             # Standalone Transaction History connection tester
├── P2Dpart6.py             # Standalone Compliance Artifact payload tester
├── P2Dpart7.py             # Standalone Transaction Exchange connection tester
├── P2Dpart8.py             # Transaction History XML engine (ISO normalization)
├── P2Dpart9.py             # Transaction Exchange engine (5-tier alternate name match)
├── P2Dpart10.py            # Artifact XML compiler (PDF-to-Base64 bundle)
├── P2Dpart11.py            # Core Pipeline Master Orchestration Control Loop
├── P2Dpart12 (1).py        # Bulk Excel state reconciliation engine
├── automation script.txt   # Step-by-step master logical flow reference
└── Instruction.txt         # Field specifications, rules, and operator runbook
