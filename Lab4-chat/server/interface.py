import select
import sys
import threading

from communication import ServerCommunication

#---CAMADA DE INTERFACE DO ADMINISTRADOR---
class ServerInterface:

    def __init__(self, hostIP, hostPort):
        #Instancia a Camada de Comunicacao:
        self.comm = ServerCommunication(hostIP, hostPort)
        #Chama a Main:
        self.main(hostIP, hostPort)

    def main(self, hostIP, hostPort):

        print("\n----Servidor de Chat Online----\n Pronto para receber conexoes.\n")
        print("Digite 'help' para ver a lista de comandos disponiveis.\n")

        inputs = [sys.stdin, self.comm.serverSocket] #lista de inputs para a funcao select

        while True:
            #Bloqueia se nao houver pedidos de conexoes novas ou comandos no buffer sys.stdin:
            r, w, e = select.select(inputs, [], [])
            for inputToBeRead in r:
                if inputToBeRead == self.comm.serverSocket:
                    self.initiateClientThread()
                elif inputToBeRead == sys.stdin:
                    adminRequest = input()
                    self.processAdminRequest(adminRequest)
            
    #Aceita conexao e delega o processamento de requisicoes deste cliente a uma nova Thread:
    def initiateClientThread(self):
        clientSocket, address = self.comm.acceptConnection()
        print("Nova conexao com " + str(address) + " estabelecida.\n")
        #Inicia uma nova thread para responder requisicoes do novo cliente com o metodo handleRequests da Camada de Comunicacao:
        clientThread = threading.Thread(target = self.comm.handleRequests, args = (clientSocket, address))
        clientThread.start()

    #Processamento de Requisicoes de Administrador:
    def processAdminRequest(self, request):
        broadcastCommands = {'broadcast', 'Broadcast', '!broadcast', '!Broadcast'}
        kickCommands = {'kick', 'Kick', '!kick', '!Kick', '!ban', '!Ban'}
        listUsersCommands = {'list', 'List', 'users', 'Users', 'lista', '!Lista', '!list', '!List', '!users', '!Users', '!lista', '!Lista', 'listusers', 'Listusers', '!listusers', '!Listusers'}
        exitCommands = {'exit', 'Exit', 'quit', 'Quit', 'disconnect', 'Disconnect', '!exit', '!Exit', '!quit', '!Quit', '!disconnect', '!Disconnect'}
        helpCommands = {'help', 'Help', '!help', '!Help'}

        validate = self.comm.validate #atribuicao realizada para melhorar legibilidade

        #Separa o request em uma lista de 2 strings no primeiro espaco encontrado:
        splitRequest = request.split(' ', 1)

        #Requisicao de Help:
        if splitRequest[0] in helpCommands:
            print("\nComandos Disponiveis ao Administrador:")
            print("help\n  Mostra esta mensagem contendo os comandos disponiveis.")
            print("list\n  Mostra a lista de todos clientes conectados no servidor e seus nomes de usuario caso estejam logados.")
            print("broadcast message\n  Envia a todos clientes conectados a mensagem 'message'.")
            print("@username message\n  Envia ao usuario de nome 'username' a mensagem 'message'. O usuario nao pode responder a mensagens de administrador.")
            print("kick username\n  Desloga o usuario de nome 'username' do servico de chat. Isso nao desconecta o usuario do servidor.")
            print("exit\n  Desconecta todos os clientes e finaliza a aplicacao servidor.\n")

        #Requisicao de Saida:
        elif splitRequest[0] in exitCommands:
            print("\nDesligando o servidor...\n")
            self.comm.serverSocket.close()
            self.comm.broadcast('$QUIT') #mensagem especial para desconectar usuarios
            sys.exit()

        #Requisicao para Mostrar Lista de Usuarios Conectados:
        elif splitRequest[0] in listUsersCommands:
            print(validate.displayConnectedUsers()) #incluira todos usuarios conectados na lista, incluindo aqueles que nao estiverem disponiveis (logados) para troca de mensagens

        #Requisicao para Deslogar um Usuario:
        elif splitRequest[0] in kickCommands:
            try:
                targetUsername = splitRequest[1].strip()
                targetSocket = validate.getSocket(targetUsername)
                if targetSocket:
                    validate.logout(targetSocket)
                    self.comm.sendTo("Voce foi deslogado remotamente pelo servidor.\nUtilize o comando de 'login' para relogar ou 'exit' para sair da aplicacao.", targetSocket)
                    print("Usuario deslogado com sucesso.")
                else:
                    print("ERRO - Usuario invalido.")
            except IndexError:
                print("ERRO - Comando deve estar no formato: kick username")

        #Requisicao de Broadcast:
        elif splitRequest[0] in broadcastCommands:
            try:
                message = splitRequest[1].strip()
                if len(message) > 0:
                    message = "[BROADCAST] " + message
                    self.comm.broadcast(message)
                    print("Mensagem enviada para todos os clientes conectados.")
                else:
                    print("ERRO - Mensagem a ser enviada nao pode conter somente espacos em branco.")
            except IndexError:
                print("ERRO - Comando deve estar no formato: broadcast message")

        #Requisicao de Mensagem a Usuario:
        elif(len(splitRequest[0]) > 0 and splitRequest[0][0] == '@'):
            targetSocket = validate.getSocket(splitRequest[0][1:])
            targetUsername = splitRequest[0][1:]
            try:
                message = splitRequest[1].strip()
                if len(message) == 0:
                    print("ERRO - Mensagem a ser enviada nao pode conter somente espacos em branco.")
                elif not validate.isUsernameAvailable(targetUsername):
                    print("ERRO - Nao ha usuarios conectados com esse nome no momento.")
                else:
                    self.comm.sendTo("[ADMIN] " + message, targetSocket)
            except IndexError:
                print("ERRO - Mensagem a ser enviada deve estar no formato: @user message")

        #Requisicao Invalida:
        else:
            print("ERRO - Comando invalido. Digite 'help' para uma lista de comandos.")