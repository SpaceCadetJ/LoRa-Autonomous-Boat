# Preserved V1 atlas evidence

[v1-netmap.json](v1-netmap.json) and [v1-netlist.xml](v1-netlist.xml) are exact copies of the two formerly ignored build artifacts used by the original atlas. Both copies match the hashes and byte counts recorded in that atlas before this portability fix. The combined payload is 105,924 bytes; it requires no CAD tools to read.

[Provenance](provenance.json) records the original paths, original atlas timestamp, export metadata, hashes, and preservation method. The release context is V1 at `639e08f`; the exact generation commit of the preserved export is not asserted. Preservation occurred while repository HEAD was observed as `a6316e9`. No primary build or CAD mutation was performed.

The atlas generator reads these preserved paths exclusively. It verifies their SHA-256 hashes and sizes against the provenance record before parsing. Local Git attributes disable newline conversion for the two byte-level snapshots. Original absolute paths inside the XML are metadata; the generator never follows them.

This is historical V1 evidence. It is not a fresh export of currently edited CAD. A new reviewed release should get its own evidence snapshot and provenance record rather than silently replacing these files. The V1 source-derived connector atlas still does not verify physical orientation or bench behavior.
