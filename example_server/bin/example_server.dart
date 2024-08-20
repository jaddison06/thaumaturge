import 'generated.dart';
import 'dart:io';
import 'PetShopController.dart';
import 'AuthController.dart';

Future main() async {
  while (true) {
    try {
      if (kApiUseHttps) {
        final https = await HttpServer.bindSecure(
          InternetAddress.anyIPv4,
          443,
          SecurityContext()
            ..useCertificateChain('/etc/ssl/cert.pem')
            ..usePrivateKey('/etc/ssl/key.pem')
        );

        await for (final request in https) {
          await handleRequest(request, PetShopController(), AuthController());
        }
      } else {
        final server = await HttpServer.bind(
          InternetAddress.anyIPv4,
          8080
        );

        await for (final request in server) {
          await handleRequest(request, PetShopController(), AuthController());
        }
      }
    } on SocketException catch (e) {
      print('Handled SocketException!\n$e');
    }
  }
}
