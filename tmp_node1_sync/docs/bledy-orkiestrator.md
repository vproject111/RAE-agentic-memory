grzegorz@grzegorz-Stealth-15M-A11SDK:~/cloud/Dockerized/RAE-agentic-memory$   source .venv/bin/activate
(.venv) grzegorz@grzegorz-Stealth-15M-A11SDK:~/cloud/Dockerized/RAE-agentic-memory$ python -m orchestrator.main --task-id RAE-DOC-001
<frozen runpy>:128: RuntimeWarning: 'orchestrator.main' found in sys.modules after import of package 'orchestrator', but prior to execution of 'orchestrator.main'; this may result in unpredictable behaviour
Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "/home/grzegorz/cloud/Dockerized/RAE-agentic-memory/orchestrator/main.py", line 524, in <module>
    asyncio.run(main())
  File "/usr/lib/python3.12/asyncio/runners.py", line 194, in run
    return runner.run(main)
           ^^^^^^^^^^^^^^^^
  File "/usr/lib/python3.12/asyncio/runners.py", line 118, in run
    return self._loop.run_until_complete(task)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3.12/asyncio/base_events.py", line 687, in run_until_complete
    return future.result()
           ^^^^^^^^^^^^^^^
  File "/home/grzegorz/cloud/Dockerized/RAE-agentic-memory/orchestrator/main.py", line 500, in main
    config = yaml.safe_load(f)
             ^^^^^^^^^^^^^^^^^
  File "/home/grzegorz/cloud/Dockerized/RAE-agentic-memory/.venv/lib/python3.12/site-packages/yaml/__init__.py", line 125, in safe_load
    return load(stream, SafeLoader)
           ^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/grzegorz/cloud/Dockerized/RAE-agentic-memory/.venv/lib/python3.12/site-packages/yaml/__init__.py", line 81, in load
    return loader.get_single_data()
           ^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/grzegorz/cloud/Dockerized/RAE-agentic-memory/.venv/lib/python3.12/site-packages/yaml/constructor.py", line 49, in get_single_data
    node = self.get_single_node()
           ^^^^^^^^^^^^^^^^^^^^^^
  File "/home/grzegorz/cloud/Dockerized/RAE-agentic-memory/.venv/lib/python3.12/site-packages/yaml/composer.py", line 36, in get_single_node
    document = self.compose_document()
               ^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/grzegorz/cloud/Dockerized/RAE-agentic-memory/.venv/lib/python3.12/site-packages/yaml/composer.py", line 55, in compose_document
    node = self.compose_node(None, None)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/grzegorz/cloud/Dockerized/RAE-agentic-memory/.venv/lib/python3.12/site-packages/yaml/composer.py", line 84, in compose_node
    node = self.compose_mapping_node(anchor)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/grzegorz/cloud/Dockerized/RAE-agentic-memory/.venv/lib/python3.12/site-packages/yaml/composer.py", line 133, in compose_mapping_node
    item_value = self.compose_node(node, item_key)
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/grzegorz/cloud/Dockerized/RAE-agentic-memory/.venv/lib/python3.12/site-packages/yaml/composer.py", line 82, in compose_node
    node = self.compose_sequence_node(anchor)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/grzegorz/cloud/Dockerized/RAE-agentic-memory/.venv/lib/python3.12/site-packages/yaml/composer.py", line 111, in compose_sequence_node
    node.value.append(self.compose_node(node, index))
                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/grzegorz/cloud/Dockerized/RAE-agentic-memory/.venv/lib/python3.12/site-packages/yaml/composer.py", line 84, in compose_node
    node = self.compose_mapping_node(anchor)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/grzegorz/cloud/Dockerized/RAE-agentic-memory/.venv/lib/python3.12/site-packages/yaml/composer.py", line 133, in compose_mapping_node
    item_value = self.compose_node(node, item_key)
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/grzegorz/cloud/Dockerized/RAE-agentic-memory/.venv/lib/python3.12/site-packages/yaml/composer.py", line 82, in compose_node
    node = self.compose_sequence_node(anchor)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/grzegorz/cloud/Dockerized/RAE-agentic-memory/.venv/lib/python3.12/site-packages/yaml/composer.py", line 111, in compose_sequence_node
    node.value.append(self.compose_node(node, index))
                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/grzegorz/cloud/Dockerized/RAE-agentic-memory/.venv/lib/python3.12/site-packages/yaml/composer.py", line 84, in compose_node
    node = self.compose_mapping_node(anchor)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/grzegorz/cloud/Dockerized/RAE-agentic-memory/.venv/lib/python3.12/site-packages/yaml/composer.py", line 133, in compose_mapping_node
    item_value = self.compose_node(node, item_key)
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/grzegorz/cloud/Dockerized/RAE-agentic-memory/.venv/lib/python3.12/site-packages/yaml/composer.py", line 64, in compose_node
    if self.check_event(AliasEvent):
       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/grzegorz/cloud/Dockerized/RAE-agentic-memory/.venv/lib/python3.12/site-packages/yaml/parser.py", line 98, in check_event
    self.current_event = self.state()
                         ^^^^^^^^^^^^
  File "/home/grzegorz/cloud/Dockerized/RAE-agentic-memory/.venv/lib/python3.12/site-packages/yaml/parser.py", line 449, in parse_block_mapping_value
    if not self.check_token(KeyToken, ValueToken, BlockEndToken):
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/grzegorz/cloud/Dockerized/RAE-agentic-memory/.venv/lib/python3.12/site-packages/yaml/scanner.py", line 116, in check_token
    self.fetch_more_tokens()
  File "/home/grzegorz/cloud/Dockerized/RAE-agentic-memory/.venv/lib/python3.12/site-packages/yaml/scanner.py", line 227, in fetch_more_tokens
    return self.fetch_alias()
           ^^^^^^^^^^^^^^^^^^
  File "/home/grzegorz/cloud/Dockerized/RAE-agentic-memory/.venv/lib/python3.12/site-packages/yaml/scanner.py", line 610, in fetch_alias
    self.tokens.append(self.scan_anchor(AliasToken))
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/grzegorz/cloud/Dockerized/RAE-agentic-memory/.venv/lib/python3.12/site-packages/yaml/scanner.py", line 922, in scan_anchor
    raise ScannerError("while scanning an %s" % name, start_mark,
yaml.scanner.ScannerError: while scanning an alias
  in ".orchestrator/tasks.yaml", line 123, column 9
expected alphabetic or numeric character, but found ' '
  in ".orchestrator/tasks.yaml", line 123, column 10
(.venv) grzegorz@grzegorz-Stealth-15M-A11SDK:~/cloud/Dockerized/RAE-agentic-memory$ 
