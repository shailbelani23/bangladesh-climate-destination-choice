PYTHON ?= python3

.PHONY: reproduce-public audit site documents validate-analysis

reproduce-public: site audit

site:
	$(PYTHON) work/build_publication_site.py

documents:
	$(PYTHON) work/publication_build/build_documents.py

audit:
	$(PYTHON) work/build_release_audit.py

validate-analysis:
	$(PYTHON) work/validate_bemp_stage1_events.py
	$(PYTHON) work/validate_bemp_stage2.py
	$(PYTHON) work/validate_bemp_stage3.py
	$(PYTHON) work/validate_and_freeze_stage4_gis.py
	$(PYTHON) work/validate_bemp_stage5.py
	$(PYTHON) work/validate_bihs_replication.py
