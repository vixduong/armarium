"""The text context-mode and rtk put in place of a long tool output (a fold). One list for write-fold-guard, which refuses
to write one over a file, and claude-md-audit's session_audit.py, which counts the folds an agent received."""
import re

CTX = (r"ctx_search\(\{queries:.*?\}\) searches the whole output"  # context-mode, Bash/REPL fold
       r"|is stored as \w+; above is the best-matching part")  # context-mode, Read fold
RTK = r"\[\+\d+ hidden: rtk recall [0-9a-f]+\]"
CTX_FOLD = re.compile(CTX, re.S)
FOLD = re.compile(CTX + "|" + RTK, re.S)
