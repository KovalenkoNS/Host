# Шаблон XML для NORMAL (CPU715)
TEMPLATE_XML_NORMAL = '''AGRAPH>><?xml version="1.0" encoding="UTF-8"?>
<BufScada>
  <Common VER="29" PageMode="4" PageID="19980" Project="otpscadabases:c:\\\\TAProject\\\\РћРђРћРќ\\\\РЎРР‘РЈР \\\\Sinopec EBSM\\\\SCADABD.GDB" isCut="false" isFFB="false" ControllerTypeName="TENIX-CPU715" ControllerID="189285" ResuorceID="627"/>
  <ISAGraf>
    <Blocks>
      <Block GROBJTYPE="31" Info="_1110_FVZ_10301B.Z2" T11ID="2136664">
        <Graphics X="650" Y="1130" WIDTH="170" HEIGHT="20"/>
        <Params T11Text=".Z2" CI="1" CO="1" VMODE="0" IsaObjId="885" cardId="672880">
          <IV>6(FALSE),TRUE,1,2(FALSE),0,6(FALSE)</IV>
        </Params>
      </Block>
      <Block GROBJTYPE="31" Info="_1110_FVZ_10301B.Z1" T11ID="2136663">
        <Graphics X="650" Y="1070" WIDTH="170" HEIGHT="20"/>
        <Params T11Text=".Z1" CI="1" CO="1" VMODE="0" IsaObjId="885" cardId="672880">
          <IV>6(FALSE),TRUE,1,2(FALSE),0,6(FALSE)</IV>
        </Params>
      </Block>
      <Block GROBJTYPE="34" Info="0" T11ID="2136608">
        <Graphics X="350" Y="1140" WIDTH="100" HEIGHT="20"/>
        <Params T11Text="0" CI="0" CO="1" VMODE="0" IsaObjId="-100" cardId="0"/>
      </Block>
      <Block GROBJTYPE="35" Info="&lt;&gt;" T11ID="2136607">
        <Graphics X="544" Y="1050" WIDTH="70" HEIGHT="60"/>
        <Params T11Text="" CI="2" CO="1" VMODE="0" IsaObjId="-8" cardId="0"/>
      </Block>
      <Block GROBJTYPE="35" Info="&lt;&gt;" T11ID="2136606">
        <Graphics X="544" Y="1110" WIDTH="70" HEIGHT="60"/>
        <Params T11Text="" CI="2" CO="1" VMODE="0" IsaObjId="-8" cardId="0"/>
      </Block>
      <Block GROBJTYPE="38" Info="[42] CDI32 &gt; канал 0.Valid" T11ID="2136605">
        <Graphics X="270" Y="1060" WIDTH="180" HEIGHT="20"/>
        <Params T11Text=".Valid" CI="0" CO="1" VMODE="0" IsaObjId="17706" cardId="575277"/>
      </Block>
      <Block GROBJTYPE="38" Info="[57] CDI32 &gt; канал 0.Valid" T11ID="2136604">
        <Graphics X="270" Y="1120" WIDTH="180" HEIGHT="20"/>
        <Params T11Text=".Valid" CI="0" CO="1" VMODE="0" IsaObjId="17706" cardId="575565"/>
      </Block>
      <Block GROBJTYPE="34" Info="0" T11ID="2136603">
        <Graphics X="350" Y="1080" WIDTH="100" HEIGHT="20"/>
        <Params T11Text="0" CI="0" CO="1" VMODE="0" IsaObjId="-100" cardId="0"/>
      </Block>
    </Blocks>
    <Gotos/>
    <Links>
      <Link Negative="false" asPointer="false" UserEdit="false" Color="0" GetBitNum="-1" ConvertTo="0">
        <PointList PL="(614,1140);(650,1140);"/>
        <FirstPoint FP="2136606|False|Result|0,0,0,0"/>
        <LastPoint LP="2136664|True|0|0,0,0,0"/>
      </Link>
      <Link Negative="false" asPointer="false" UserEdit="false" Color="0" GetBitNum="-1" ConvertTo="0">
        <PointList PL="(614,1080);(650,1080);"/>
        <FirstPoint FP="2136607|False|Result|0,0,0,0"/>
        <LastPoint LP="2136663|True|0|0,0,0,0"/>
      </Link>
      <Link Negative="false" asPointer="false" UserEdit="false" Color="0" GetBitNum="-1" ConvertTo="0">
        <PointList PL="(450,1150);(544,1150);"/>
        <FirstPoint FP="2136608|False|0|0,0,0,0"/>
        <LastPoint LP="2136606|True|1|0,0,0,0"/>
      </Link>
      <Link Negative="false" asPointer="false" UserEdit="false" Color="0" GetBitNum="-1" ConvertTo="0">
        <PointList PL="(450,1130);(544,1130);"/>
        <FirstPoint FP="2136604|False|0|0,0,0,0"/>
        <LastPoint LP="2136606|True|0|0,0,0,0"/>
      </Link>
      <Link Negative="false" asPointer="false" UserEdit="false" Color="0" GetBitNum="-1" ConvertTo="0">
        <PointList PL="(450,1090);(544,1090);"/>
        <FirstPoint FP="2136603|False|0|0,0,0,0"/>
        <LastPoint LP="2136607|True|1|0,0,0,0"/>
      </Link>
      <Link Negative="false" asPointer="false" UserEdit="false" Color="0" GetBitNum="-1" ConvertTo="0">
        <PointList PL="(450,1070);(544,1070);"/>
        <FirstPoint FP="2136605|False|0|0,0,0,0"/>
        <LastPoint LP="2136607|True|0|0,0,0,0"/>
      </Link>
    </Links>
  </ISAGraf>
  <GrObj/>
  <ISAOBJSINFO>
    <rec ID="885" Info="DDR_v1"/>
  </ISAOBJSINFO>
  <ISACARDSINFO>
    <rec ID="575277" Info="_IO_IU46_0" IsRetain="-1" Name="[42] CDI32 &gt; РєР°РЅР°Р» 0" SSize="0" KLPath=""/>
    <rec ID="575565" Info="_IO_IU47_0" IsRetain="-1" Name="[57] CDI32 &gt; РєР°РЅР°Р» 0" SSize="0" KLPath=""/>
    <rec ID="672880" Info="_1110_FVZ_10301B" IsRetain="-1" Name="Ethylene into R-101" SSize="0" KLPath="Р РЎРЈ\\\\x08EBSM\\\\x08DI0010-01R"/>
  </ISACARDSINFO>
</BufScada>'''

# Шаблон XML для VAL (CPU850)
TEMPLATE_XML_VAL = '''AGRAPH>><?xml version="1.0" encoding="UTF-8"?>
<BufScada>
  <Common VER="29" PageMode="4" PageID="20240" Project="otpscadabases:c:\\TAProject\\РћРђРћРќ\\РЎРР‘РЈР \\Sinopec EBSM\\SCADABD.GDB" isCut="false" isFFB="false" ControllerTypeName="TENIX-CPU850" ControllerID="189290" ResuorceID="623"/>
  <ISAGraf>
    <Blocks>
      <Block GROBJTYPE="38" Info="[6] DI32 &gt;DI32 êàíàë 12 &gt; VAL.Quality" T11ID="2140432">
        <Graphics X="910" Y="200" WIDTH="310" HEIGHT="20"/>
        <Params T11Text=".Quality" CI="0" CO="1" VMODE="0" IsaObjId="6127" cardId="565520"/>
      </Block>
      <Block GROBJTYPE="38" Info="[22] DI32 &gt;DI32 êàíàë 12 &gt; VAL.Quality" T11ID="2140433">
        <Graphics X="910" Y="260" WIDTH="310" HEIGHT="20"/>
        <Params T11Text=".Quality" CI="0" CO="1" VMODE="0" IsaObjId="6127" cardId="567008"/>
      </Block>
      <Block GROBJTYPE="36" Info="QUAL_STAT" T11ID="2140434">
        <Graphics X="1260" Y="190" WIDTH="90" HEIGHT="40"/>
        <Params T11Text="" CI="1" CO="1" VMODE="0" IsaObjId="17611" cardId="0"/>
      </Block>
      <Block GROBJTYPE="36" Info="QUAL_STAT" T11ID="2140435">
        <Graphics X="1260" Y="250" WIDTH="90" HEIGHT="40"/>
        <Params T11Text="" CI="1" CO="1" VMODE="0" IsaObjId="17611" cardId="0"/>
      </Block>
      <Block GROBJTYPE="31" Info="_1110_FZZSC_10502.Z1" T11ID="2140436">
        <Graphics X="1470" Y="210" WIDTH="210" HEIGHT="20"/>
        <Params T11Text=".Z1" CI="1" CO="1" VMODE="0" IsaObjId="885" cardId="706630">
          <IV>6(FALSE),TRUE,1,2(FALSE),0,6(FALSE)</IV>
        </Params>
      </Block>
      <Block GROBJTYPE="31" Info="_1110_FZZSC_10502.Z2" T11ID="2140437">
        <Graphics X="1470" Y="270" WIDTH="210" HEIGHT="20"/>
        <Params T11Text=".Z2" CI="1" CO="1" VMODE="0" IsaObjId="885" cardId="706630">
          <IV>6(FALSE),TRUE,1,2(FALSE),0,6(FALSE)</IV>
        </Params>
      </Block>
      <Block GROBJTYPE="34" Info="0" T11ID="2142662">
        <Graphics X="1250" Y="230" WIDTH="100" HEIGHT="20"/>
        <Params T11Text="0" CI="0" CO="1" VMODE="0" IsaObjId="-100" cardId="0"/>
      </Block>
      <Block GROBJTYPE="35" Info="&lt;&gt;" T11ID="2142663">
        <Graphics X="1380" Y="190" WIDTH="70" HEIGHT="60"/>
        <Params T11Text="" CI="2" CO="1" VMODE="0" IsaObjId="-8" cardId="0"/>
      </Block>
      <Block GROBJTYPE="34" Info="0" T11ID="2142667">
        <Graphics X="1250" Y="290" WIDTH="100" HEIGHT="20"/>
        <Params T11Text="0" CI="0" CO="1" VMODE="0" IsaObjId="-100" cardId="0"/>
      </Block>
      <Block GROBJTYPE="35" Info="&lt;&gt;" T11ID="2142668">
        <Graphics X="1380" Y="250" WIDTH="70" HEIGHT="60"/>
        <Params T11Text="" CI="2" CO="1" VMODE="0" IsaObjId="-8" cardId="0"/>
      </Block>
    </Blocks>
    <Gotos/>
    <Links>
      <Link Negative="false" asPointer="false" UserEdit="false" Color="0" GetBitNum="-1" ConvertTo="0">
        <PointList PL="(1220,210);(1260,210);"/>
        <FirstPoint FP="2140432|False|0|0,0,0,0"/>
        <LastPoint LP="2140434|True|QUAL|0,0,0,0"/>
      </Link>
      <Link Negative="false" asPointer="false" UserEdit="false" Color="0" GetBitNum="-1" ConvertTo="0">
        <PointList PL="(1220,270);(1260,270);"/>
        <FirstPoint FP="2140433|False|0|0,0,0,0"/>
        <LastPoint LP="2140435|True|QUAL|0,0,0,0"/>
      </Link>
      <Link Negative="false" asPointer="false" UserEdit="false" Color="0" GetBitNum="-1" ConvertTo="0">
        <PointList PL="(1350,240);(1360,240);(1360,230);(1380,230);"/>
        <FirstPoint FP="2142662|False|0|0,0,0,0"/>
        <LastPoint LP="2142663|True|1|0,0,0,0"/>
      </Link>
      <Link Negative="false" asPointer="false" UserEdit="false" Color="0" GetBitNum="-1" ConvertTo="0">
        <PointList PL="(1350,210);(1380,210);"/>
        <FirstPoint FP="2140434|False|Result|0,0,0,0"/>
        <LastPoint LP="2142663|True|0|0,0,0,0"/>
      </Link>
      <Link Negative="false" asPointer="false" UserEdit="false" Color="0" GetBitNum="-1" ConvertTo="0">
        <PointList PL="(1450,220);(1470,220);"/>
        <FirstPoint FP="2142663|False|Result|0,0,0,0"/>
        <LastPoint LP="2140436|True|0|0,0,0,0"/>
      </Link>
      <Link Negative="false" asPointer="false" UserEdit="false" Color="0" GetBitNum="-1" ConvertTo="0">
        <PointList PL="(1350,300);(1360,300);(1360,290);(1380,290);"/>
        <FirstPoint FP="2142667|False|0|0,0,0,0"/>
        <LastPoint LP="2142668|True|1|0,0,0,0"/>
      </Link>
      <Link Negative="false" asPointer="false" UserEdit="false" Color="0" GetBitNum="-1" ConvertTo="0">
        <PointList PL="(1350,270);(1380,270);"/>
        <FirstPoint FP="2140435|False|Result|0,0,0,0"/>
        <LastPoint LP="2142668|True|0|0,0,0,0"/>
      </Link>
      <Link Negative="false" asPointer="false" UserEdit="false" Color="0" GetBitNum="-1" ConvertTo="0">
        <PointList PL="(1450,280);(1470,280);"/>
        <FirstPoint FP="2142668|False|Result|0,0,0,0"/>
        <LastPoint LP="2140437|True|0|0,0,0,0"/>
      </Link>
    </Links>
  </ISAGraf>
  <GrObj/>
  <ISAOBJSINFO>
    <rec ID="885" Info="DDR_v1"/>
    <rec ID="17611" Info="QUAL_STAT"/>
  </ISAOBJSINFO>
  <ISACARDSINFO>
    <rec ID="565520" Info="_IO_I11_DI32_12_VAL" IsRetain="-1" Name="[6] DI32 &gt;DI32 ÐºÐ°Ð½Ð°Ð» 12 &gt; VAL" SSize="0" KLPath=""/>
    <rec ID="567008" Info="_IO_I16_DI32_12_VAL" IsRetain="-1" Name="[22] DI32 &gt;DI32 ÐºÐ°Ð½Ð°Ð» 12 &gt; VAL" SSize="0" KLPath=""/>
    <rec ID="706630" Info="_1110_FZZSC_10502" IsRetain="1" Name="Ethylene into R-103 Bed2" SSize="0" KLPath="РџРђР—\\x08EBSM\\x08SDI0010-02R"/>
  </ISACARDSINFO>
</BufScada>'''