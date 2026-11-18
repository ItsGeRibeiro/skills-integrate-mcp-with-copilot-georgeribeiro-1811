# API de Atividades da Mergington High School

Uma aplicação FastAPI para consultar atividades extracurriculares e gerenciar inscrições.

## Funcionalidades

- Visualizar atividades e suas listas de participantes sem login
- Inscrever ou remover estudantes quando autenticado como professor

## Primeiros Passos

Execute os comandos a partir da raiz do repositório, com o ambiente virtual ativado.

1. Instale as dependências:

   ```
   python -m pip install -r requirements.txt
   ```

2. Crie uma conta de professor com `python -m src.teacher_auth nome-do-professor`.
   O comando solicita a senha no terminal e salva apenas o hash com salt no arquivo
   local `src/teachers.local.json`, ignorado pelo Git. Repita para cada professor.
3. Execute a aplicação com `python -m uvicorn src.app:app`.
4. Abra seu navegador e vá para:
   - Site: http://localhost:8000 (use o ícone de pessoa para entrar como professor)
   - Documentação da API: http://localhost:8000/docs
   - Documentação alternativa: http://localhost:8000/redoc

A sessão expira em oito horas e é encerrada no logout ou ao reiniciar o servidor.
As sessões são mantidas em memória; execute com um único processo e use HTTPS fora do ambiente local.

## Endpoints da API

| Método | Endpoint                                                          | Descrição                                                           |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Obter todas as atividades com seus detalhes e contagem atual de participantes |
| POST   | `/auth/login` | Iniciar uma sessão com `username` e `password` no corpo JSON |
| GET    | `/auth/session` | Verificar a sessão de professor |
| POST   | `/auth/logout` | Encerrar a sessão de professor |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Inscrever um estudante (professor) |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Remover a inscrição de um estudante (professor) |

Ao chamar a API diretamente, envie `X-Teacher-Action: 1` nas requisições `POST` e
`DELETE` e reutilize o cookie de sessão recebido no login para gerenciar inscrições.

## Testes

Instale as dependências de teste com `python -m pip install -r requirements-dev.txt`
e execute `python -m unittest discover -s tests`.

## Modelo de Dados

A aplicação usa um modelo de dados simples com identificadores significativos:

1. **Atividades** - Usa o nome da atividade como identificador:

   - Descrição
   - Cronograma
   - Número máximo de participantes permitidos
   - Lista de emails de estudantes que estão inscritos

2. **Estudantes** - Usa email como identificador:
   - Nome
   - Nível da série

Todos os dados são armazenados na memória, o que significa que os dados serão resetados quando o servidor reiniciar.
