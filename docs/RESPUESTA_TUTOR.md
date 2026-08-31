# Borrador de respuesta al tutor

Buenos días, Carmelo:

Muchas gracias por la revisión y por las indicaciones. He mantenido la
Modalidad 5 y he preparado una nueva versión centrada en los puntos que
señalabas.

He ampliado la parte experimental con la procedencia, tamaño y distribución de
los conjuntos utilizados; la separación entre entrenamiento, calibración y
prueba; las métricas de accuracy, precisión, recall y F1; y las matrices de
confusión de los modos heurístico, neuronal y combinado. También he añadido la
discusión de resultados y sus límites, unas conclusiones generales vinculadas
al cumplimiento de los objetivos y capturas reales del prototipo.

En concreto, he rehecho el entrenamiento para que sea reproducible y evitar
fuga de datos. El modelo español usa 1.148 textos limpios y 209 del split
oficial de prueba. El inglés ya no suma el CSV agregado y sus seis componentes:
deduplica el agregado a 82.077 textos y lo divide 80/20 con semilla 42 en
65.661 para entrenamiento y 16.416 para prueba. El repositorio fija las URLs,
licencias y SHA-256 de las fuentes, verifica los CSV externos y permite
reentrenar y regenerar las métricas sin versionar mensajes brutos.

Además, he documentado los cambios respecto a la propuesta inicial, en
particular la sustitución de TensorFlow por el MLP de scikit-learn y la decisión
de mantener un análisis local y estático sin reputación online ni validación de
certificados. La memoria aclara también que SPF, DKIM y DMARC no se verifican
activamente: el sistema interpreta los resultados que ya aparecen en las
cabeceras del correo.

He revisado la bibliografía completa, eliminado entradas no citadas, verificado
la correspondencia de los identificadores de arXiv y añadido la referencia del
benchmark externo. El repositorio incluye dependencias fijadas, instrucciones
de ejecución, pruebas automáticas, los datos de evaluación reproducibles y un
guion de demostración.

Siguiendo tu indicación, he añadido en la metodología una mención breve al uso
de herramientas de inteligencia artificial como apoyo para consultas técnicas,
resolución de errores, revisión de código, CSS y documentación. También aclaro
que las decisiones y la interpretación de los resultados son responsabilidad
del autor y que la IA no se ha utilizado como fuente académica: la parte
teórica se ha contrastado y citado mediante las referencias originales.

Para ver el sistema en directo por Teams puedo adaptarme a estas franjas:

- [DÍA Y HORA 1]
- [DÍA Y HORA 2]
- [DÍA Y HORA 3]

Si ninguna te encaja, indícame otra y me organizo. Te envío adjunta la nueva
memoria y el enlace al repositorio.

Un saludo,

Alejandro Villarrubia García
