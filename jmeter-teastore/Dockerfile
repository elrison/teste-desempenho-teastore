# Usa uma imagem base do JMeter
FROM justb4/jmeter:latest

# Define o diretório de trabalho
WORKDIR /opt/jmeter

# 1. Cria o diretório lib/ext, caso não exista
RUN mkdir -p /opt/jmeter/lib/ext

# 2. Baixa o Gerenciador de Plugins para a pasta criada
RUN wget -q https://jmeter-plugins.org/get/ -O /opt/jmeter/lib/ext/plugins-manager.jar

# # 3. Instala o utilitário de linha de comando (CMDRunner)
# RUN java -cp /opt/jmeter/lib/ext/plugins-manager.jar org.jmeterplugins.repository.PluginManagerCMDInstaller

# # 4. Usa o utilitário para instalar o plugin 'CSS Selector Extractor'
# RUN /opt/jmeter/bin/PluginsManagerCMD.sh install jpgc-css-selectors