// Copia de textos/prueba-0001-v12-n2-1.json para abrir la aplicación sin servidor.
(window.DATOS_REVISTAS = window.DATOS_REVISTAS || {})["textos/prueba-0001-v12-n2-1.json"] = {
 "version": 1,
 "recogido": "2026-10-17T00:00:00+00:00",
 "doi": "10.0000/prueba-0001.0.1",
 "titulo": "Artículo de prueba 1: una aproximación ficticia al estudio de trabajo de cuidados",
 "es_prueba": true,
 "licencia": {
  "codigo": "by",
  "nombre": "CC BY 4.0",
  "nombre_completo": "Creative Commons Atribución 4.0 Internacional",
  "url": "https://creativecommons.org/licenses/by/4.0/",
  "url_legal": "https://creativecommons.org/licenses/by/4.0/legalcode.es"
 },
 "fuente": {
  "url": "https://example.org/prueba-0001/articulo/0-1",
  "formato": "HTML",
  "plataforma": "datos de prueba",
  "pagina": "https://example.org/prueba-0001/articulo/0-1"
 },
 "autores_cita": [
  {
   "apellidos": "Autora de Prueba",
   "nombre_pila": "Persona",
   "nombre": null
  },
  {
   "apellidos": "Ficticia",
   "nombre_pila": "Otra Persona",
   "nombre": null
  }
 ],
 "avisos_derechos": [
  "Copyright (c) 2026 Persona Autora de Prueba. Aviso de derechos ficticio."
 ],
 "idioma_principal": "es",
 "indice": [
  {
   "id": "t-s1-titulo",
   "nivel": 2,
   "texto": "Introducción",
   "lang": null
  },
  {
   "id": "t-s1-1",
   "nivel": 3,
   "texto": "Objetivos",
   "lang": null
  },
  {
   "id": "t-s2-titulo",
   "nivel": 2,
   "texto": "Resultados",
   "lang": null
  },
  {
   "id": "t-notas-titulo",
   "nivel": 2,
   "texto": "Notas",
   "lang": null
  },
  {
   "id": "t-referencias-titulo",
   "nivel": 2,
   "texto": "Referencias",
   "lang": null
  }
 ],
 "vueltas": {
  "t-nota-1": "t-llamada-nota-1-1",
  "t-nota-2": "t-llamada-nota-2-1",
  "t-ref-1": "t-llamada-ref-1-1"
 },
 "contenido": [
  [
   "section",
   {
    "id": "t-s1"
   },
   [
    "h2",
    {
     "id": "t-s1-titulo"
    },
    "Introducción"
   ],
   [
    "p",
    {},
    "Texto de prueba. Este artículo no existe: sirve para comprobar la vista de lectura. Incluye una llamada a nota",
    [
     "sup",
     {},
     [
      "a",
      {
       "href": "#t-nota-1",
       "id": "t-llamada-nota-1-1"
      },
      "1"
     ]
    ],
    " y una cita a la bibliografía (",
    [
     "a",
     {
      "href": "#t-ref-1",
      "id": "t-llamada-ref-1-1"
     },
     "Autora Ficticia, 2020"
    ],
    ")."
   ],
   [
    "p",
    {
     "lang": "en"
    },
    "This paragraph is written in English to check that screen readers switch voice."
   ],
   [
    "blockquote",
    {},
    [
     "p",
     {},
     "Una cita textual larga de prueba, con su propio formato."
    ]
   ],
   [
    "h3",
    {
     "id": "t-s1-1"
    },
    "Objetivos"
   ],
   [
    "ul",
    {},
    [
     "li",
     {},
     "Primer objetivo de prueba."
    ],
    [
     "li",
     {},
     "Segundo objetivo de prueba",
     [
      "sup",
      {},
      [
       "a",
       {
        "href": "#t-nota-2",
        "id": "t-llamada-nota-2-1"
       },
       "2"
      ]
     ],
     "."
    ]
   ]
  ],
  [
   "section",
   {
    "id": "t-s2"
   },
   [
    "h2",
    {
     "id": "t-s2-titulo"
    },
    "Resultados"
   ],
   [
    "figure",
    {
     "id": "t-tabla-1"
    },
    [
     "table",
     {},
     [
      "caption",
      {},
      "Tabla 1. Casos ficticios por año y territorio"
     ],
     [
      "thead",
      {},
      [
       "tr",
       {},
       [
        "th",
        {
         "scope": "col"
        },
        "Año"
       ],
       [
        "th",
        {
         "scope": "col"
        },
        "Territorio norte"
       ],
       [
        "th",
        {
         "scope": "col"
        },
        "Territorio sur"
       ],
       [
        "th",
        {
         "scope": "col"
        },
        "Territorio este"
       ],
       [
        "th",
        {
         "scope": "col"
        },
        "Territorio oeste"
       ],
       [
        "th",
        {
         "scope": "col"
        },
        "Territorio central"
       ],
       [
        "th",
        {
         "scope": "col"
        },
        "Total"
       ]
      ]
     ],
     [
      "tbody",
      {},
      [
       "tr",
       {},
       [
        "th",
        {
         "scope": "row"
        },
        "2021"
       ],
       [
        "td",
        {},
        "5"
       ],
       [
        "td",
        {},
        "6"
       ],
       [
        "td",
        {},
        "7"
       ],
       [
        "td",
        {},
        "8"
       ],
       [
        "td",
        {},
        "9"
       ],
       [
        "td",
        {},
        "10"
       ]
      ],
      [
       "tr",
       {},
       [
        "th",
        {
         "scope": "row"
        },
        "2022"
       ],
       [
        "td",
        {},
        "6"
       ],
       [
        "td",
        {},
        "7"
       ],
       [
        "td",
        {},
        "8"
       ],
       [
        "td",
        {},
        "9"
       ],
       [
        "td",
        {},
        "10"
       ],
       [
        "td",
        {},
        "11"
       ]
      ],
      [
       "tr",
       {},
       [
        "th",
        {
         "scope": "row"
        },
        "2023"
       ],
       [
        "td",
        {},
        "0"
       ],
       [
        "td",
        {},
        "1"
       ],
       [
        "td",
        {},
        "2"
       ],
       [
        "td",
        {},
        "3"
       ],
       [
        "td",
        {},
        "4"
       ],
       [
        "td",
        {},
        "5"
       ]
      ]
     ]
    ]
   ],
   [
    "figure",
    {
     "id": "t-figura-1"
    },
    [
     "figcaption",
     {},
     "Figura 1. Evolución ficticia de los casos"
    ],
    [
     "figura",
     {
      "alt": "Gráfico de líneas que sube de 5 casos en 2021 a 9 en 2023."
     }
    ]
   ],
   [
    "figure",
    {
     "id": "t-figura-2"
    },
    [
     "figcaption",
     {},
     "Figura 2. Mapa ficticio sin descripción"
    ],
    [
     "figura",
     {}
    ]
   ],
   [
    "p",
    {},
    "Más información en ",
    [
     "a",
     {
      "href": "https://example.org/proyecto"
     },
     "la web ficticia del proyecto"
    ],
    "."
   ]
  ],
  [
   "section",
   {
    "id": "t-notas"
   },
   [
    "h2",
    {
     "id": "t-notas-titulo"
    },
    "Notas"
   ],
   [
    "aside",
    {
     "id": "t-nota-1",
     "rol": "fn"
    },
    [
     "p",
     {},
     "1. Primera nota de prueba."
    ]
   ],
   [
    "aside",
    {
     "id": "t-nota-2",
     "rol": "fn"
    },
    [
     "p",
     {},
     "2. Segunda nota de prueba."
    ]
   ]
  ],
  [
   "section",
   {
    "id": "t-referencias"
   },
   [
    "h2",
    {
     "id": "t-referencias-titulo"
    },
    "Referencias"
   ],
   [
    "p",
    {
     "id": "t-ref-1",
     "rol": "ref"
    },
    "Autora Ficticia, A. (2020). ",
    [
     "i",
     {},
     "Libro de prueba"
    ],
    ". Editorial de Ejemplo."
   ]
  ]
 ]
};
