# SESI Conecta — publicação externa

Pacote preparado para hospedagem no Railway ou outro serviço compatível com Docker. A publicação externa ainda depende de uma conta conectada e da configuração do serviço.

## Configuração de publicação

- Dockerfile na raiz: reconhecido automaticamente pelo Railway.
- Inicialização: `python servidor.py` (definida no Dockerfile).
- Escuta em 0.0.0.0 na variável PORT fornecida pela hospedagem.
- Verificação de disponibilidade: `/health`.
- Um volume persistente montado em `/data` guarda o SQLite e mantém o histórico após novas publicações.
- Apenas uma instância/replica do serviço, para compartilhar o mesmo arquivo SQLite.
- Variáveis HOSTED=1 e DATA_DIR=/data já estão definidas no Dockerfile.
- Gerar um domínio público do serviço após publicar. O endereço final será fornecido pela hospedagem; ainda não existe um endereço Railway para este projeto.

Este pacote inicia um banco novo. Ele não contém o histórico nem os códigos de grupos do site atual. Qualquer migração do histórico deve ser planejada separadamente; não apague o site atual.

## Como usar depois de publicar

Abra o link HTTPS da hospedagem, escolha nome e avatar e crie um grupo. Envie o link e o código aos colegas. Eles não precisam de conta no ChatGPT. O código continua necessário para escolher qual grupo acessar.

## Alterações para hospedagem

O servidor aceita a porta fornecida pela plataforma, salva o banco no volume persistente, verifica a origem HTTPS nas operações de escrita e usa cookies de sessão HttpOnly, SameSite=Lax e Secure. A interface permanece em HTML, CSS e JavaScript, sem dependências externas.

Os nomes são apelidos sem verificação de identidade. Conversas privadas são filtradas no servidor, mas não têm criptografia de ponta a ponta. A interface busca novidades a cada dois segundos e mostra as últimas 200 mensagens disponíveis ao participante.

## Testes executados

Envio público e privado, isolamento entre grupos, idempotência, reações, permissões de exclusão, respostas, indicador de digitação, saída de sessão, proteção do banco, endpoint de disponibilidade, validação de origem HTTPS e cookie Secure. A publicação no provedor externo ainda não foi executada.

## Referências de configuração

https://docs.railway.com/builds/dockerfiles
https://docs.railway.com/deployments/healthchecks
https://docs.railway.com/volumes/reference
https://docs.railway.com/networking/domains/working-with-domains


## Enviar ao GitHub e publicar

1. Entre em https://github.com/new e crie um repositório chamado `sesi-conecta`.
2. Extraia este pacote. Em Add file → Upload files, envie o conteúdo da pasta `SESI_Conecta_Hospedagem`, não o arquivo ZIP. Confirme em Commit changes.
3. `Dockerfile`, `servidor.py` e `schema.sql` devem estar na raiz do repositório; preserve os arquivos dentro de `public/`.
4. No Railway, crie um projeto e escolha a opção de publicar a partir de um repositório GitHub. Vincule sua conta do GitHub e selecione o repositório.
5. Configure um volume persistente no serviço, montado em `/data`, antes de começar a usar o chat. Mantenha uma única instância do serviço.
6. Configure a verificação de disponibilidade em `/health`. O Dockerfile já define como iniciar o aplicativo e ele usa a porta da hospedagem.
7. Publique. Em Settings → Networking, use Generate Domain para gerar o link público.
8. Abra o endereço HTTPS, crie um grupo e compartilhe o link e o código com os participantes.

O GitHub armazena o código. GitHub Pages hospeda páginas estáticas e não executa o servidor Python deste projeto. O Railway executa o servidor e permite persistir o banco em um volume. Confira o plano e os custos exibidos na sua conta antes de contratar recursos.

Este pacote foi atualizado com o botão Mensagem privada, busca de destinatário, aviso de conversa privada, rascunhos separados e proteção do indicador de digitação nas conversas privadas. Ainda não foi publicado em uma hospedagem externa.


Atualização: a página principal agora é public/index.html, e o banco pode ser inicializado novamente sem perder o histórico ou falhar por tabelas existentes. A versão hospedada atende a raiz / e usa os mesmos arquivos do projeto testado no VS Code.
