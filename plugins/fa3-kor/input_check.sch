<?xml version="1.0" encoding="UTF-8"?>
<schema xmlns="http://purl.oclc.org/dsdl/schematron" queryBinding="xslt">
  <ns prefix="fa" uri="http://crd.gov.pl/wzor/2025/06/25/13775/"/>

  <pattern>
    <rule context="fa:Fa">
      <assert test="fa:RodzajFaktury = 'VAT'">
        RodzajFaktury must be 'VAT', found '<value-of select="fa:RodzajFaktury"/>'
      </assert>

      <assert test="fa:P_14_1W">
        P_14_1W is missing
      </assert>
      <assert test="not(fa:P_14_1W) or number(fa:P_14_1W) = 0">
        P_14_1W must be zero, found '<value-of select="fa:P_14_1W"/>'
      </assert>

      <assert test="fa:P_14_1">
        P_14_1 is missing
      </assert>
      <assert test="not(fa:P_14_1) or number(fa:P_14_1) != 0">
        P_14_1 must be non-zero
      </assert>

      <assert test="not(fa:P_13_2 | fa:P_13_3 | fa:P_13_4 | fa:P_13_5 |
                        fa:P_13_6_1 | fa:P_13_6_2 | fa:P_13_6_3 |
                        fa:P_13_7 | fa:P_13_8 | fa:P_13_9 | fa:P_13_10 | fa:P_13_11)">
        Unexpected P_13 fields present (only P_13_1 is allowed)
      </assert>
    </rule>
  </pattern>
</schema>
