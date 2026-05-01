<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="2.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns="http://crd.gov.pl/wzor/2025/06/25/13775/"
    xpath-default-namespace="http://crd.gov.pl/wzor/2025/06/25/13775/"
    exclude-result-prefixes="#all">

  <xsl:output method="xml" encoding="UTF-8" indent="yes"/>

  <!-- Path to the lookup XML file; passed by the runner as a file URI -->
  <xsl:param name="lookupFile" select="''"/>
  <xsl:variable name="invoicesDoc"
      select="if ($lookupFile != '') then doc($lookupFile) else ()"/>

  <!-- Identity transform: copy everything as-is -->
  <xsl:template match="@* | node()">
    <xsl:copy>
      <xsl:apply-templates select="@* | node()"/>
    </xsl:copy>
  </xsl:template>

  <!-- Append _cor to the invoice number -->
  <xsl:template match="P_2">
    <xsl:copy>
      <xsl:value-of select="concat(., '_cor')"/>
    </xsl:copy>
  </xsl:template>

  <!-- Set issue date to today -->
  <xsl:template match="P_1">
    <xsl:copy>
      <xsl:value-of select="format-date(current-date(), '[Y0001]-[M01]-[D01]')"/>
    </xsl:copy>
  </xsl:template>

  <!-- Inside FaWiersz: keep only NrWierszaFa -->
  <xsl:template match="FaWiersz/*[not(self::NrWierszaFa)]"/>

  <!-- Zero all summary amount fields except P_14_1W -->
  <xsl:template match="P_13_1 | P_13_2 | P_13_3 | P_13_4 | P_13_5 |
                       P_13_6_1 | P_13_6_2 | P_13_6_3 |
                       P_13_7 | P_13_8 | P_13_9 | P_13_10 | P_13_11 |
                       P_14_1 | P_14_2 | P_14_2W | P_14_3 | P_14_3W |
                       P_14_4 | P_14_4W | P_14_5 |
                       P_15 | P_15Z | P_15ZK">
    <xsl:copy>0.00</xsl:copy>
  </xsl:template>

  <!-- Change invoice type to KOR and inject correction metadata -->
  <xsl:template match="RodzajFaktury">
    <xsl:variable name="invoiceNumber" select="../P_2"/>
    <xsl:variable name="inv"
        select="$invoicesDoc/*/*[*[local-name()='number'] = $invoiceNumber]"/>
    <xsl:copy>KOR</xsl:copy>
    <PrzyczynaKorekty>wrong TAX amount in PLN</PrzyczynaKorekty>
    <TypKorekty>1</TypKorekty>
    <DaneFaKorygowanej>
      <DataWystFaKorygowanej><xsl:value-of select="$inv/*[local-name()='date']"/></DataWystFaKorygowanej>
      <NrFaKorygowanej><xsl:value-of select="$invoiceNumber"/></NrFaKorygowanej>
      <NrKSeF>1</NrKSeF>
      <NrKSeFFaKorygowanej><xsl:value-of select="$inv/*[local-name()='ksefNumber']"/></NrKSeFFaKorygowanej>
    </DaneFaKorygowanej>
  </xsl:template>

  <!-- Set P_14_1W from the lookup, matched by invoice number -->
  <xsl:template match="P_14_1W">
    <xsl:variable name="invoiceNumber" select="../P_2"/>
    <xsl:variable name="taxAmount"
        select="$invoicesDoc/*/*[*[local-name()='number'] = $invoiceNumber]/*[local-name()='taxAmountPLN']"/>
    <xsl:copy>
      <xsl:value-of select="if ($taxAmount) then $taxAmount else '0.00'"/>
    </xsl:copy>
  </xsl:template>

</xsl:stylesheet>
