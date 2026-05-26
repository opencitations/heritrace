# SPDX-FileCopyrightText: 2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

FROM openlink/virtuoso-opensource-7:7.2-alpine

RUN apk add --no-cache python3 py3-requests curl

COPY data /data
COPY scripts /scripts
COPY config/virtuoso_dataset.ini /config/virtuoso_dataset.ini
COPY config/virtuoso_provenance.ini /config/virtuoso_provenance.ini

ENTRYPOINT ["/scripts/entrypoint.sh"]
