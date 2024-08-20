import 'dart:typed_data';
import 'dart:convert';
import 'package:pointycastle/export.dart';
import 'package:pointycastle/pointycastle.dart';


extension on Uint8List {
  String toHexString() {
    StringBuffer buffer = new StringBuffer();
    for (int part in this) {
      if (part & 0xff != part) {
        throw new FormatException("Non-byte integer detected");
      }
      buffer.write('${part < 16 ? '0' : ''}${part.toRadixString(16)}');
    }
    return buffer.toString();
  }
}

extension on String {
  Uint8List toUint8List() => Uint8List.fromList(utf8.encode(this));
}

String hashPassword(String password, String salt) {
  final saltBytes = salt.toUint8List();

  final params = Argon2Parameters(
    Argon2Parameters.ARGON2_id,
    saltBytes,
    iterations: 3,
    memoryPowerOf2: 12,
    desiredKeyLength: 32
  );
  final hash = Argon2BytesGenerator();
  hash.init(params);

  final passwordBytes = password.toUint8List();
  final hashedPassword = hash.process(passwordBytes);

  return hashedPassword.toHexString();
}