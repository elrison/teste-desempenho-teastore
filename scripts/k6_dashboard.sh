#!/bin/bash

mkdir -p k6-html

echo "📊 Gerando dashboard HTML para K6 SIMPLE..."
k6 run k6-teastore/teste-carga-simples.js \
  --out web-dashboard=k6-html/k6-simple.html || true

echo "📊 Gerando dashboard HTML para K6 COMPLEX..."
k6 run k6-teastore/cenarios-complexos.js \
  --out web-dashboard=k6-html/k6-complex.html || true

echo "✅ Dashboards K6 prontos!"
