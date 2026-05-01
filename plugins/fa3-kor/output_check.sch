<?xml version="1.0" encoding="UTF-8"?>
<schema xmlns="http://purl.oclc.org/dsdl/schematron" queryBinding="xslt">
  <ns prefix="fa" uri="http://crd.gov.pl/wzor/2025/06/25/13775/"/>

  <pattern>
    <rule context="fa:Fa">
      <assert test="fa:P_14_1W">
        P_14_1W is missing or zero
      </assert>
      <assert test="not(fa:P_14_1W) or number(fa:P_14_1W) != 0">
        P_14_1W must be non-zero
      </assert>

      <assert test="not(fa:P_13_1)   or number(fa:P_13_1)   = 0">P_13_1 must be zero, found '<value-of select="fa:P_13_1"/>'</assert>
      <assert test="not(fa:P_13_2)   or number(fa:P_13_2)   = 0">P_13_2 must be zero, found '<value-of select="fa:P_13_2"/>'</assert>
      <assert test="not(fa:P_13_3)   or number(fa:P_13_3)   = 0">P_13_3 must be zero, found '<value-of select="fa:P_13_3"/>'</assert>
      <assert test="not(fa:P_13_4)   or number(fa:P_13_4)   = 0">P_13_4 must be zero, found '<value-of select="fa:P_13_4"/>'</assert>
      <assert test="not(fa:P_13_5)   or number(fa:P_13_5)   = 0">P_13_5 must be zero, found '<value-of select="fa:P_13_5"/>'</assert>
      <assert test="not(fa:P_13_6_1) or number(fa:P_13_6_1) = 0">P_13_6_1 must be zero, found '<value-of select="fa:P_13_6_1"/>'</assert>
      <assert test="not(fa:P_13_6_2) or number(fa:P_13_6_2) = 0">P_13_6_2 must be zero, found '<value-of select="fa:P_13_6_2"/>'</assert>
      <assert test="not(fa:P_13_6_3) or number(fa:P_13_6_3) = 0">P_13_6_3 must be zero, found '<value-of select="fa:P_13_6_3"/>'</assert>
      <assert test="not(fa:P_13_7)   or number(fa:P_13_7)   = 0">P_13_7 must be zero, found '<value-of select="fa:P_13_7"/>'</assert>
      <assert test="not(fa:P_13_8)   or number(fa:P_13_8)   = 0">P_13_8 must be zero, found '<value-of select="fa:P_13_8"/>'</assert>
      <assert test="not(fa:P_13_9)   or number(fa:P_13_9)   = 0">P_13_9 must be zero, found '<value-of select="fa:P_13_9"/>'</assert>
      <assert test="not(fa:P_13_10)  or number(fa:P_13_10)  = 0">P_13_10 must be zero, found '<value-of select="fa:P_13_10"/>'</assert>
      <assert test="not(fa:P_13_11)  or number(fa:P_13_11)  = 0">P_13_11 must be zero, found '<value-of select="fa:P_13_11"/>'</assert>
      <assert test="not(fa:P_14_1)   or number(fa:P_14_1)   = 0">P_14_1 must be zero, found '<value-of select="fa:P_14_1"/>'</assert>
      <assert test="not(fa:P_14_2)   or number(fa:P_14_2)   = 0">P_14_2 must be zero, found '<value-of select="fa:P_14_2"/>'</assert>
      <assert test="not(fa:P_14_2W)  or number(fa:P_14_2W)  = 0">P_14_2W must be zero, found '<value-of select="fa:P_14_2W"/>'</assert>
      <assert test="not(fa:P_14_3)   or number(fa:P_14_3)   = 0">P_14_3 must be zero, found '<value-of select="fa:P_14_3"/>'</assert>
      <assert test="not(fa:P_14_3W)  or number(fa:P_14_3W)  = 0">P_14_3W must be zero, found '<value-of select="fa:P_14_3W"/>'</assert>
      <assert test="not(fa:P_14_4)   or number(fa:P_14_4)   = 0">P_14_4 must be zero, found '<value-of select="fa:P_14_4"/>'</assert>
      <assert test="not(fa:P_14_4W)  or number(fa:P_14_4W)  = 0">P_14_4W must be zero, found '<value-of select="fa:P_14_4W"/>'</assert>
      <assert test="not(fa:P_14_5)   or number(fa:P_14_5)   = 0">P_14_5 must be zero, found '<value-of select="fa:P_14_5"/>'</assert>
      <assert test="not(fa:P_15)     or number(fa:P_15)     = 0">P_15 must be zero, found '<value-of select="fa:P_15"/>'</assert>
      <assert test="not(fa:P_15Z)    or number(fa:P_15Z)    = 0">P_15Z must be zero, found '<value-of select="fa:P_15Z"/>'</assert>
      <assert test="not(fa:P_15ZK)   or number(fa:P_15ZK)   = 0">P_15ZK must be zero, found '<value-of select="fa:P_15ZK"/>'</assert>
    </rule>
  </pattern>
</schema>
