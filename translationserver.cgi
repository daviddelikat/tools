#!/data/wre/prereqs/bin/perl

use strict;
use CGI;
use CGI::Carp qw (fatalsToBrowser);
use Config::JSON;
use URI::Escape;
use Data::Dumper;
use Encode qw(decode_utf8 encode);

#-----main----------------
my $wgi18neditRoot = "/data/domains/translation.webgui.org/";


 my $config = Config::JSON->new($wgi18neditRoot.'/etc/i18n.conf');

 our $outputPath = $config->get("outputPath");
 our $webguiPath = $config->get("webguiPath");
 our $editor_lang = $config->get("editor_lang");
 our $extras_url = $config->get("extras_url");

 binmode(STDOUT, ":utf8");

 $|=1; # disable output buffer

if ($ARGV[0] eq "--calculate") {
	calculateCompletion();
	exit;
}

our $cgi = CGI->new;
our $languageId = $cgi->param("languageId");
##Sanitize the languageId, english ASCII only
$languageId =~ tr/a-zA-Z_0-9//dc;

our $editor_on;

if ($cgi->param("is_editor_on") ne "") {
 	our $editor_cookie = $cgi->cookie(-name=>'visual_editor_on', -expires=>'+48h', -value=>[$cgi->param("is_editor_on")]);
 	print $cgi->header( -cookie=>$editor_cookie, -expires=>'-1d', -charset=>"UTF-8");
 	$editor_on = $cgi->param("is_editor_on");
}
else {
 	print $cgi->header( -charset=>"UTF-8");
 	$editor_on = $cgi->cookie('visual_editor_on');
}


if ($cgi->param("op") eq "buildSiteFrames") {
	print buildSiteFrames();
	my $lang = getLanguage($languageId);
}
elsif ($cgi->param("op") ne "") {
 	print header();
 	if ($cgi->param("op") =~ /^[[:alpha:]]+$/) {
 		my $cmd = "&www_".$cgi->param("op");
 		print eval($cmd);
	}
	else {
 		print "<h1>Stop Screwing Around</h1>";
	}
 	print footer();
}
else {
	print header();
 	print buildMainScreen();
	print footer();
}

#-----end main------------

#------------------------------------------------------
sub buildMainScreen {
	opendir(DIR,$outputPath);
	my @files = readdir(DIR);
	closedir(DIR);
	my $out = '<h1>WebGUI Translation Server</h1><fieldset><legend>Choose An Existing Language To Edit</legend><img src="/i18n.gif" align="right" border="0" alt="Translation Server" />';
	foreach my $file (sort @files) {
		next unless -d $outputPath."/".$file;
		next if $file =~ m{\A\.};
		next if $file eq "..";
		$languageId = $file;
         	my $downloadUrl = buildURL('exportTranslation');
		$out .= '<form method="post" style="margin:0px"><input type="hidden" name="op" value="buildSiteFrames"><input type="hidden" name="languageId" value="'.$languageId.'"><a href="'.$downloadUrl.'">Download</a>&nbsp;<input type="submit" value="edit"> '.$languageId.' (';
		open my $complete, "<", $outputPath."/".$languageId.".complete";
		my $percent = <$complete>;
		close $complete;
		$out .= $percent."% Complete)</form>\n";

	}
	$out .= q|<p><b>NOTE:</b> The RedNeck language is there for demo purposes. You can use it to play around.</p></fieldset>|;
	$out .= <<STOP;
	<br>
	<fieldset>
	<legend>Create A New Language</legend>
	<form method="post">
	<input type="hidden" name="op" value="buildSiteFrames">
	<input type="text" name="languageId"><input type="submit" value="create"><br />
	Type a system friendly name for your language. Alpha numeric characters, not spaces, no special characters. You'll have the option to set the human friendly name next.
	</form>
	</fieldset>
STOP
	return $out;
}

#------------------------------------------------------
sub calculateCompletion {
    local $languageId;
	opendir(DIR,$outputPath);
	my @files = readdir(DIR);
	closedir(DIR);
	foreach my $file (sort @files) {
		next unless -d $outputPath."/".$file;
		next if $file =~ m{\A\.};
		next if $file eq "..";
		$languageId = $file;

		# calc percentages of completion
        my $total = 0;
        my $ood = 0;
 		my $namespaces = getNamespaces();
        	foreach my $namespace (@{$namespaces}) {
                	my $eng = getNamespaceItems($namespace);
                	my $lang = getNamespaceItems($namespace,$languageId);
                	foreach my $tag (keys %{$eng}) {
                        	$total++;
                        	if ($lang->{$tag}{message} eq "" || $eng->{$tag}{lastUpdated} >= $lang->{$tag}{lastUpdated}) {
                                	$ood++;
                        	}
                	}
        	}
        my $percent = ($total > 0) ? sprintf('%.1f',(($total - $ood) / $total)*100) : 0;
        if ($ood && $ood < $total/1000) {
            $percent = '99.9';
        }
		open(my $complete, ">", $outputPath."/".$languageId.".complete");
		print $complete $percent;
		close $complete;
	}
}

#------------------------------------------------------

sub languageIdIsBad {
	return ($languageId =~ m/English|\s+/ || $languageId !~ m/^[A-Z]/);
}

#------------------------------------------------------
sub buildSiteFrames {
	if (languageIdIsBad()) {
		return buildMainScreen();
	}
 	my $output = '
 <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Frameset//EN"
    "http://www.w3.org/TR/html4/frameset.dtd">
 <html>
 <head><title>WebGUI Internationalization Editor</title></head>
 <frameset cols="300,*">
 <frame name="menu" src="'.buildURL("displayMenu").'">
 <frame name="editor" src="'.buildURL("editLanguage").'">
 </frameset>
 </html>
 ';
 	return $output;
 }

#------------------------------------------------------
sub buildURL {
 	my $op = shift;
 	my $params = shift;
 	my $url = '/?op='.$op.';languageId='.$languageId;
 	foreach my $param (keys %{$params}) {
 		$url .= ';'.$param.'='.uri_escape($params->{$param});
 	}
 	return $url;
}

#------------------------------------------------------
sub fixFormData {
    my $value = shift;
    $value =~ s/\&/\&amp\;/g;
    $value =~ s/\"/\&quot\;/g;
    $value =~ s/\</\&lt\;/g;
    $value =~ s/\>/\&gt\;/g;
    return $value;
}

#------------------------------------------------------
sub footer {
 	return '</body></html>';
}

#------------------------------------------------------
sub getLanguage {
 	my $load = $outputPath.'/'.$languageId.'/'.$languageId.'.pm';
 	eval {require $load};
 	if ($@) {
 		writeLanguage();
 		return getLanguage();
 	}
	else {
 		my $cmd = "\$WebGUI::i18n::".$languageId."::LANGUAGE";
 		return eval ($cmd);
 	}
}

#------------------------------------------------------
sub getNamespaceItems {
 	my $namespace = shift;
 	my $languageId = shift || "English";
 	my $inLoop = shift;
 	my $load;
 	if ($languageId eq "English") {
 		$load = $webguiPath.'/lib/WebGUI/i18n/English/'.$namespace.'.pm';
 	}
	else {
 		$load = $outputPath.'/'.$languageId.'/'.$languageId.'/'.$namespace.'.pm';
 	}
 	eval {require $load};
 	if ($@ && !$inLoop) {
 		writeNamespace($namespace);
 		return getNamespaceItems($namespace,$languageId, 1);
 	}
	else {
 		my $cmd = "\$WebGUI::i18n::".$languageId."::".$namespace."::I18N";
 		return eval($cmd);
 	}
}

#------------------------------------------------------
sub getNamespaces {
    opendir (my $dh, $webguiPath.'/lib/WebGUI/i18n/English/');
    my @files = sort readdir($dh);
    closedir($dh);
    my @namespaces;
    foreach my $file (@files) {
        if ($file =~ /(.*?)\.pm$/) {
            push(@namespaces,$1);
        }
    }
    return \@namespaces;
}

#------------------------------------------------------
sub header {
 my $editor_page =<<EOHEADER;
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html><head><meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />

<META HTTP-EQUIV="Pragma" CONTENT="no-cache">
<META HTTP-EQUIV="Cache-Control" CONTENT="no-cache, must-revalidate">
<META HTTP-EQUIV="Expires" CONTENT="Mon, 26 Jul 1997 05:00:00 GMT">
<META HTTP-EQUIV="Expires" CONTENT="-1">

<style>
	th {
		text-align: left;
		font-weight: bold;
		font-size: 85%;
		background-color: #f0f0f0;
		font-family: sans, helvetica, arial;
		white-space: nowrap;
	}
	.outOfDate {
		background-color: #ffff77;
		font-weight: bold;
	}
	.allGood {
		background-color: #aaffaa;
	}
	.undefined {
		background-color: #ffaaaa;
		font-weight: bold;
	}
    .editItemRow div {
        padding-top: 2px;
        padding-bottom: 2px;
        padding-right: 2px;
    }
    .editItemRow label {
        float: left;
        width: 15%;
		text-align: left;
		font-weight: bold;
		background-color: #f0f0f0;
		font-family: sans, helvetica, arial;
    }
    .editItemRow span {
        float: right;
        width: 80%;
    }
    .editItemRow span span {
        float: none;
        width: auto;
    }
</style>
<!-- YUI Simple Editor -->
<!-- Skin CSS file -->
<link rel="stylesheet" type="text/css" href="$extras_url/yui/build/assets/skins/sam/skin.css">
<!-- Utility Dependencies -->
<script type="text/javascript" src="$extras_url/yui/build/yahoo-dom-event/yahoo-dom-event.js"></script>
<script type="text/javascript" src="$extras_url/yui/build/element/element-beta.js"></script>
<!-- Needed for Menus, Buttons and Overlays used in the Toolbar -->
<script src="$extras_url/yui/build/container/container_core-min.js"></script>
<script src="$extras_url/yui/build/button/button-min.js"></script>
<!-- Source file for Rich Text Editor-->
<script src="$extras_url/yui/build/editor/simpleeditor-min.js"></script>
</head><body>
EOHEADER
 	return $editor_page;
}

#------------------------------------------------------
sub preview {
 	my $text = shift || "not yet defined";
 	$text = substr($text,0,50);
 	$text =~ s/&/&amp;/g;
 	$text =~ s/\</&lt;/g;
 	$text =~ s/\>/&gt;/g;
 	return $text;
}

#------------------------------------------------------
sub setLanguage {
 	my $label = shift;
 	my $toolbar = shift;
	my $translit = shift;
	my $languageAbbreviation = shift;
	my $locale = shift;
    local $Data::Dumper::Terse = 1;
    local $Data::Dumper::Sortkeys = 1;
    local $Data::Dumper::Indent = 1;
    local $Data::Dumper::Useperl  = 1;
    my $output = Dumper({
        label                   => $label,
        toolbar                 => $toolbar,
        languageAbbreviation    => $languageAbbreviation,
        locale                  => $locale,
    });
 	writeLanguage($output, $translit);
}

#------------------------------------------------------
sub setNamespaceItems {
 	my $namespace = shift;
 	my $tag = shift;
 	my $message = shift;
 	my $lang = getNamespaceItems($namespace,$languageId);
 	$lang->{$tag}{message} = $message;
 	$lang->{$tag}{lastUpdated} = time();
    # Get rid of $VAR1 prefix
    local $Data::Dumper::Terse    = 1;
    local $Data::Dumper::Sortkeys = 1;
    local $Data::Dumper::Indent   = 1;
    local $Data::Dumper::Useperl  = 1;
    my $output = Dumper($lang);
 	writeNamespace($namespace,$output);
}

#------------------------------------------------------
sub writeFile {
    my $filepath = shift;
    my $content = shift;
    my $mkdir = substr($filepath,1,(length($filepath)-1));
    my @path = split("\/",$mkdir);
    $mkdir = "";
    foreach my $part (@path) {
        next if ($part =~ /\.pm/);
        $mkdir .= "/".$part;
        mkdir($mkdir);
    }
    if (open(my $fh,">:utf8", $filepath)) {
        print {$fh} $content;
        close($fh);
    }
    else {
        print "ERROR writing file ".$filepath." because ".$!.".\n";
        exit;
    }
}

#------------------------------------------------------
sub writeLanguage {
    my $data = shift || '{}';
	my $translit_replaces_r = shift;
 	my $output = "package WebGUI::i18n::".$languageId.";\n\n";
 	$output .= "use strict;\n";
    $output .= "use utf8;\n\n";
    $output .= "our \$LANGUAGE = ";
    $output .= $data;
    $output .= ";\n\n";

 $translit_replaces_r =~ s/\r//g; # For ***nix OS

    $output .= qq(sub makeUrlCompliant {
    my \$value = shift;\n);
 $output .= "##<-- start transliteration -->##\n".$translit_replaces_r."\n##<-- end transliteration -->##\n";
 $output .= <<'END_TRANSLIT';
    $value =~ s/\s+$//;                     #removes trailing whitespace
    $value =~ s/^\s+//;                     #removes leading whitespace
    $value =~ s/ /-/g;                      #replaces whitespace with underscores
    $value =~ s/\.$//;                      #removes trailing period
    $value =~ s/[^A-Za-z0-9._\/-]//g;       #removes all funky characters
    $value =~ s{//+}{/}g;                   #removes double /
    $value =~ s{^/}{};                      #removes a preceeding /
    return $value;
}
END_TRANSLIT
 	$output .= "\n\n1;\n";
 	writeFile($outputPath.'/'.$languageId.'/'.$languageId.'.pm', $output);
}

#------------------------------------------------------
sub writeNamespace {
 	my $namespace = shift;
 	my $data = shift || '{}';
 	my $output = "package WebGUI::i18n::".$languageId."::".$namespace.";\nuse utf8;\n";
 	$output .= "our \$I18N = ";
 	$output .= $data;
 	$output .= ";\n\n1;\n";
 	writeFile($outputPath.'/'.$languageId.'/'.$languageId.'/'.$namespace.'.pm', $output);
}

#------------------------------------------------------
sub www_commitTranslation {
	if (languageIdIsBad()) {
		return '';
	}
	calculateCompletion();
	chdir($outputPath);
    ##Merge in outside changes, preferring our version for all conflicts
	my $rawChanges = `git status --porcelain $languageId`;
	my @changes = split m{\n}, $rawChanges;
	CHANGE: foreach my $change (@changes) {
        ##Fixed width parse, 2 character, 1 space, then all characters
        print "change: $change<br />\n";
		my ($type, undef, $file) = unpack "A2AA*", $change;
        next CHANGE if $file =~ /\.complete$/;
		if (($type eq "??") && ($file !~ m{\.r.*$}) ) {
			print "Adding ".$file."<br />\n";
			system("git add $file");
		}
        elsif ($type eq " M") {
			print "Updating ".$file."<br />\n";
		}
#        elsif ($type eq "C") {
#            # Resolve any conflicts by overriding changes on the server by the local version
#            print "Resolving conflict in ".$file."<br />";
#            system("/usr/bin/svn --accept mine-full resolve $file");
#        }
	}
	print "Preparing to commit local changes<br />\n";
    my $out;
	$out = `git commit -m 'Updating $languageId on translation server' $languageId;`;
	$out .= `git fetch origin`;
	$out .= `git merge -s recursive -X ours origin`;
	$out .= `git push`;

	return '<br /><pre>'.$out.'</pre>';
}

#------------------------------------------------------
sub www_displayMenu {
	if (languageIdIsBad()) {
		return '';
	}
 	my $output = '
		<a href="/" target="_top">HOME</a><br /><br />
		'.$languageId.'<br />
		&bull; <a href="'.buildURL("editLanguage").'" target="editor">Edit</a><br />
		&bull; <a href="'.buildURL("exportTranslation").'" target="editor">Export</a><br />
		&bull; <a href="'.buildURL("commitTranslation").'" target="editor">Commit</a><br />
		&bull; <a href="'.buildURL("translatorsNotes").'" target="editor">Translators Notes</a><br />
		<br /><table>';
 	my $namespaces = getNamespaces();
 	foreach my $namespace (@{$namespaces}) {
 		my $eng = getNamespaceItems($namespace);
 		my $lang = getNamespaceItems($namespace,$languageId);
		my $total = 0;
		my $ood = 0;
 		foreach my $tag (keys %{$eng}) {
			$total++;
 			if ($lang->{$tag}{message} eq "" || $eng->{$tag}{lastUpdated} >= $lang->{$tag}{lastUpdated}) {
				$ood++;
 			}
 		}
		my $percent = ($total > 0) ? int((($total - $ood) / $total) * 100) : 0;
 		$output .= '<tr><td class="'.(($percent == 0) ? 'undefined' : ($percent < 100) ? 'outOfDate' : 'allGood').'">'.$percent.'%</td><td><a href="'.buildURL("listItemsInNamespace",{namespace=>$namespace}).'" target="editor">'.$namespace.'</a></td><td>'.($total - $ood).'/'.$total.'</td></tr>';
 	}
	$output .= '</table>';
 	return $output;
}

#------------------------------------------------------
sub www_editItem {
    my $namespace   = $cgi->param('namespace');
 	my $eng = getNamespaceItems($namespace);
 	my $lang = getNamespaceItems($namespace,$languageId);
    my $tag         = $cgi->param('tag');
    my $message     = fixFormData($lang->{$tag}{message});
    my $origMessage = $eng->{$tag}{message};
    my $origContext = $eng->{$tag}{context};
    my $editorBoolean = $editor_on ? 'true' : 'false';
    my $output =<<EOFORM;
<div class="yui-skin-sam">
<form id="editForm" name="editForm" method="post" action="/#$tag">
<input type="hidden" name="languageId" value="$languageId">
<input type="hidden" name="namespace" value="$namespace">
<input type="hidden" name="tag" value="$tag">
<input type="hidden" name="op" value="editItemSave">
<input type="hidden" name="is_editor_on" id="is_editor_on" value="$editor_on">
<fieldset class="editItemRow">
<legend>Translate Item</legend>
<div>
<label></label>
<span><button type="button" id="toggleEditor">Toggle Editor</button></span>
<div style="clear: both;"></div>
</div>
<div>
<label>Namespace</label>
<span>$namespace</span>
<div style="clear: both;"></div>
</div>
<div>
<label>Namespace</label>
<span>$namespace</span>
<div style="clear: both;"></div>
</div>
<div>
<label>Tag</label>
<span>$tag</span>
<div style="clear: both;"></div>
</div>
<div>
<label>Message</label>
<span><textarea style="width: 100%" rows="10" name="message" id="message">$message</textarea></span>
<div style="clear: both;"></div>
</div>
<div>
<label></label>
<span><input type="submit" name="saveMessage" id="saveMessage" value="Save" />
</span>
<div style="clear: both;"></div>
</div>
<div>
<label>Original Message</label>
<span>$origMessage</span>
<div style="clear: both;"></div>
</div>
<div>
<label>Context Info</label>
<span>$origContext</span>
<div style="clear: both;"></div>
</div>
</form>
</fieldset>
</form>
<script type="text/javascript">
(function() {
    var Dom = YAHOO.util.Dom,
        Event = YAHOO.util.Event;

    var _toggleButton = new YAHOO.widget.Button('toggleEditor');

    var myConfig = {
        handleSubmit: true,
        height: '200px',
        width: '650px',
        animate: true,
        dompath: true,
        focusAtStart: true
    };

    var formToggle = document.getElementById('is_editor_on');

    var toggleState = $editorBoolean;

    _toggleButton.on('click', function(ev) {
        Event.stopEvent(ev);
        if (toggleState) {
            toggleState = false;
            formToggle.value = 0;
        }
        else {
            toggleState = true;
            formToggle.value = 1;
        }
        handleEditorDraw(toggleState);
    });
    var myEditor;
    function handleEditorDraw (myState) {
        if (myState) { //Draw it
            if (! myEditor) {
                myEditor = new YAHOO.widget.SimpleEditor('message', myConfig);
                myEditor.render();
            }
        }
        else { //Hide it
            if (myEditor) {
                myEditor.destroy();
                myEditor = null;
            }
        }
    }
    handleEditorDraw(toggleState);
})();
</script>
</div>
EOFORM
 	return $output;
}

#------------------------------------------------------
sub www_editItemSave {
    warn "saving message:<".$cgi->param("message").">\n";
    my $english = getNamespaces();
    my $namespace = $cgi->param("namespace");
    my %namespaces = map { $_ => 1 } @{ $english };
    if (exists $namespaces{$namespace}) {
        setNamespaceItems($namespace,$cgi->param("tag"),decode_utf8($cgi->param("message")));
    }
 	return '<script type="text/javascript">parent.frames[0].location.reload();</script>Message saved.<p />'.www_listItemsInNamespace();
}

#------------------------------------------------------
sub www_editLanguage {
	if (languageIdIsBad()) {
		return '';
	}
 	my $lang = getLanguage();
 	my $output = '<form method="post"><table width="95%">';
 	$output .= '<input type="hidden" name="languageId" value="'.$languageId.'">';
 	$output .= '<input type="hidden" name="op" value="editLanguageSave">';
 	$output .= '<tr><th>Label</th><td><input type="text" name="label" value="'.$lang->{label}.'"><br />A human readable name for your language.</td></tr>';
 	$output .= '<tr><th>Toolbar</th><td><input type="text" name="toolbar" value="'.$lang->{toolbar}.'"><br />Use "bullet" without the quotes if you don\'t plan to create your own toolbar.</td></tr>';
 	$output .= '<tr><th>Language Abbreviation</th><td><input type="text" name="languageAbbreviation" value="'.$lang->{languageAbbreviation}.'"><br />This is the standard international two digit language code, which will be used by some javascripts and perl modules. For English it is "en".</td></tr>';
 	$output .= '<tr><th>Locale</th><td><input type="text" name="locale" value="'.$lang->{locale}.'"><br />This is the standard international two digit country abbreviation, which will be used by some javascripts and perl modules. For the United States it is "US".</td></tr>';
 	$output .= '<tr><th>Replaces for transliteration<br /><br />Something like:<br /><pre>';
    $output .= <<END_TRANSLIT;
\$value =~ s/\x{419}\x{430}/J\\'a/;
\$value =~ s/\x{439}\x{430}/j\\'a/;
\$value =~ s/\x{419}\x{410}/J\\'A/;
\$value =~ s/\x{42f}/Ja/g;
\$value =~ s/\x{44f}/ja/g;

\$value =~ s/^\\s+//;
\$value =~ s/^\\\\//;
\$value =~ s/ /_/g;
\$value =~ s/\\.\\\$//;
\$value =~ s/[^A-Za-z0-9\\-\\.\\_\\/]//g;
\$value =~ s/^\\///;
\$value =~ s/\\/\\//\\//g;
END_TRANSLIT
    $output .= '</pre></th><td width="100%"><textarea style="width: 100%;" rows="20" name="translit_replaces">'.fixFormData(ReadTranslit()).'</textarea><br />Transliterations are used in making URLs and file names conform to a usable standard. URLs and file names often can\'t deal with special characters used by various non-English languages. As such, those characters need to be transliterated into English characters.</td></tr>';
 	$output .= '<tr><th></th><td><input type="submit" value="Save"></td></tr>';
 	$output .= '</table></form>';
 	return $output;
}

#------------------------------------------------------
sub www_editLanguageSave {
    setLanguage(decode_utf8($cgi->param("label")), $cgi->param("toolbar"), decode_utf8($cgi->param("translit_replaces")), $cgi->param("languageAbbreviation"), $cgi->param("locale"));
	calculateCompletion();
 	return "Language saved.<p>".www_editLanguage();
}

#------------------------------------------------------
sub www_exportTranslation {
	if (languageIdIsBad()) {
		return '';
	}
	calculateCompletion();
	chdir($outputPath);
	system("tar cfz ".$languageId.".tar.gz --exclude=.svn ".$languageId);
	return '<a href="/translations/'.$languageId.'.tar.gz">Download '.$languageId.'.tar.gz</a>';
}


#------------------------------------------------------
sub www_listItemsInNamespace {
 	my $eng = getNamespaceItems($cgi->param("namespace"));
 	my $lang = getNamespaceItems($cgi->param("namespace"),$languageId);
 	my $output = '<table width="95%">';
 	$output .= '<tr><th>Namespace</th><th>'.$cgi->param("namespace").'</th></tr>';
	my $total = 0;
	my $ood = 0;
 	foreach my $tag (sort keys %{$eng}) {
		$total++;
 		$output .= '<tr class="';
 		if ($lang->{$tag}{message} eq "") {
			$ood++;
 			$output .= 'undefined';
 		} elsif ($eng->{$tag}{lastUpdated} >= $lang->{$tag}{lastUpdated}) {
			$ood++;
 			$output .= 'outOfDate';
 		} else {
			$output .= 'allGood';
		}
 		$output .= '"><td><a name="'.$tag.'" href="'.buildURL("editItem",{namespace=>$cgi->param("namespace"),tag=>$tag}).'">'.$tag.'</a></td><td>';
 		if ($lang->{$tag} ne "") {
 			$output .= preview($lang->{$tag}{message});
 		} else {
 			$output .= preview($eng->{$tag}{message});
 		}
 		$output .= '</td></tr>';
 	}
 	$output .= '</table>';
	$output = 'Status: '.sprintf('%.4f',(($total - $ood) / $total)*100).'% ('.($total - $ood).' / '.$total.') Complete  <br />'.$output;
 	return $output;
}

#------------------------------------------------------
sub www_translatorsNotes {
    open (my $notesFile, "<:utf8", $outputPath.'/'.$languageId.'/notes.txt');
    my $notes = do { local $/; <$notesFile> };
    close($notesFile);
 	my $output = '<form method="post"><table width="95%">';
 	$output .= '<input type="hidden" name="languageId" value="'.$languageId.'">';
 	$output .= '<input type="hidden" name="op" value="translatorsNotesSave">';
    $output .= '<th></th><td width="100%"><textarea style="width: 100%;" rows="40" name="notes">'.fixFormData($notes).'</textarea><br />Place any notes of interest here including common dictionary terms, translation notes, and a list of people who worked on this translation. This text will go into the translation distribution, but will not be displayed anywhere on the site, or affect system performance.</td></tr>';
 	$output .= '<tr><th></th><td><input type="submit" value="Save"></td></tr>';
 	$output .= '</table></form>';
 	return $output;
}

#------------------------------------------------------
sub www_translatorsNotesSave {
	open(my $notesFile, ">:utf8", $outputPath.'/'.$languageId.'/notes.txt');
	print {$notesFile} decode_utf8($cgi->param("notes"))."\n";
	close($notesFile);
 	return "Notes saved.<p>".www_translatorsNotes();
}

#------------------------------------------------------
sub ReadTranslit {
    open(my $translit, '<:utf8', "$outputPath/$languageId/$languageId.pm") || die "$!\n";
    my $flag_T = 0;
    my $translit_replaces_read = '';
    while (my $translit = <$translit>) {
        if ($translit =~ /##<-- end transliteration -->##/) {
            $flag_T = 0;
            next;
        }
        if ($translit =~ /##<-- start transliteration -->##/) {
            $flag_T = 1;
            next;
        }
        if ($flag_T == 1) {
            $translit_replaces_read .= $translit;
        }
    }
    close $translit;
    return $translit_replaces_read;
}


__END__

=head2 Changelog

=item * Dec 26, 2008

Implemented RFE: Less lines in i18n editor  (#9350).  Changed number of lines from 30 to 10.
