#!/data/wre/prereqs/bin/perl
 
use strict;
use CGI qw (:standart);
use CGI::Carp qw (fatalsToBrowser);
use Config::JSON;
use URI::Escape;
use Text::Iconv;
use Data::Dumper;
 
 #-----main----------------
my $wgi18neditRoot = "/data/domains/translation.webgui.org/";
 
 
 my $config = Config::JSON->new($wgi18neditRoot.'/etc/i18n.conf');
 
 our $outputPath = $config->get("outputPath");
 our $webguiPath = $config->get("webguiPath");
 our $editor_lang = $config->get("editor_lang");
 our $extras_url = $config->get("extras_url");
 
 $|=1; # disable output buffer
 our $cgi = CGI->new;
 our $languageId = $cgi->param("languageId");

 our $editor_on;
 
 if ($cgi->param("is_editor_on") ne "") {
 
 our $editor_cookie;
 $editor_cookie = $cgi->cookie(-name=>'visual_editor_on',
 							-expires=>'+48h',
                         	-value=>[$cgi->param("is_editor_on")]);
 
 print $cgi->header(
 	-cookie=>$editor_cookie,
 	-expires=>'-1d',
 	-charset=>"UTF-8"
 		);
 $editor_on = $cgi->param("is_editor_on");
 } else {
 print $cgi->header(
 	-charset=>"UTF-8"
 		);
 $editor_on = $cgi->cookie('visual_editor_on');
 }
 
 
if ($cgi->param("op") eq "buildSiteFrames") {
	print buildSiteFrames();
	my $lang = getLanguage($languageId);
} elsif ($cgi->param("op") ne "") {
 	print header();
 	if ($cgi->param("op") =~ /^[[:alpha:]]+$/) {
 		my $cmd = "&www_".$cgi->param("op");
 		print eval($cmd);
	} else {
 		print "<h1>Stop Screwing Around</h1>";
	}	
 	print footer();
} else {
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
		next if $file =~ m{\A\.};
		next if $file eq "..";
		next if $file =~ m/\.tar\.gz$/;
		next if $file eq "servernames";
		$languageId = $file;
         	my $downloadUrl = buildURL('exportTranslation');
		$out .= '<form method="post" style="margin:0px"><input type="hidden" name="op" value="buildSiteFrames"><input type="hidden" name="languageId" value="'.$file.'"><a href="'.$downloadUrl.'">Download</a>&nbsp;<input type="submit" value="edit"> '.$file.' (';

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
         $value =~ s/\"/\&quot\;/g;
         $value =~ s/\&/\&amp\;/g;
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
 	} else {
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
 	} else {
 		$load = $outputPath.'/'.$languageId.'/'.$languageId.'/'.$namespace.'.pm';
 	}
 	eval {require $load};
 	if ($@ && !$inLoop) {
 		writeNamespace($namespace);
 		return getNamespaceItems($namespace,$languageId, 1);
 	} else {
 		my $cmd = "\$WebGUI::i18n::".$languageId."::".$namespace."::I18N";
 		return eval($cmd);
 	}
 }
 
 #------------------------------------------------------
sub getNamespaces {
 	opendir (DIR,$webguiPath.'/lib/WebGUI/i18n/English/');
        	my @files = readdir(DIR);
        	closedir(DIR);
 	@files = sort @files;
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
 my $editor_page;
 $editor_page = "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.01 Transitional//EN\"\r\n";
 $editor_page .= "   \"http://www.w3.org/TR/html4/loose.dtd\">\r\n";
 $editor_page .= "<html><head><meta http-equiv=\"Content-Type\" content=\"text/html; charset=UTF-8\" />\r\n";
 
 $editor_page .= qq(<META HTTP-EQUIV="Pragma" CONTENT="no-cache">\r\n);
 $editor_page .= qq(<META HTTP-EQUIV="Cache-Control" CONTENT="no-cache, must-revalidate">\r\n);
 $editor_page .= qq(<META HTTP-EQUIV="Expires" CONTENT="Mon, 26 Jul 1997 05:00:00 GMT">\r\n);
 $editor_page .= qq(<META HTTP-EQUIV="Expires" CONTENT="-1">\r\n);
 
 $editor_page .= "<style>\r\n";
 $editor_page .= "	th {\r\n";
 $editor_page .= "		text-align: left;\r\n";
 $editor_page .= "		font-weight: bold;\r\n";
 $editor_page .= "		font-size: 85%;\r\n";
 $editor_page .= "		background-color: #f0f0f0;\r\n";
 $editor_page .= "		font-family: sans, helvetica, arial;\r\n";
 $editor_page .= "		white-space: nowrap;\r\n";
 $editor_page .= "	}\r\n";
 $editor_page .= "	.outOfDate {\r\n";
 $editor_page .= "		background-color: #ffff77;\r\n";
 $editor_page .= "		font-weight: bold;\r\n";
 $editor_page .= "	}\r\n";
 $editor_page .= "	.allGood {\r\n";
 $editor_page .= "		background-color: #aaffaa;\r\n";
 $editor_page .= "	}\r\n";
 $editor_page .= "	.undefined {\r\n";
 $editor_page .= "		background-color: #ffaaaa;\r\n";
 $editor_page .= "		font-weight: bold;\r\n";
 $editor_page .= "	}\r\n";
 $editor_page .= "</style>\r\n";
 if (!$editor_on == 1) {
 $editor_page .= "<!-- tinyMCE -->\r\n";
 $editor_page .= "<script language=\"javascript\" type=\"text/javascript\" src=\"$extras_url/tinymce2/jscripts/tiny_mce/tiny_mce.js\"></script>";
 $editor_page .= "<script language=\"javascript\" type=\"text/javascript\">\r\n";
 $editor_page .= "   tinyMCE.init({\r\n";
 $editor_page .= "       mode : \"specific_textareas\",\r\n";
 $editor_page .= "    	theme : \"advanced\",\r\n";
 $editor_page .= "       theme_advanced_disable : \"help,image\",\r\n";
 $editor_page .= "      language : \"$editor_lang\",\r\n";
 $editor_page .= "    content_css : \"/site.css\",\r\n";
 $editor_page .= "	auto_reset_designmode : \"true\"\r\n";
 $editor_page .= "   })\;\r\n";
 $editor_page .= "</script>\r\n";
 $editor_page .= "<!-- /tinyMCE -->\r\n";
 }
 $editor_page .= "</head><body>";
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
 	my $output = "\tlabel => '".$label."',\n";
 	$output .= "\ttoolbar => '".$toolbar."',\n";
 	$output .= "\tlanguageAbbreviation => '".$languageAbbreviation."',\n";
 	$output .= "\tlocale => '".$locale."',\n";
 	writeLanguage($output, $translit);
 }
 
 #------------------------------------------------------
sub setNamespaceItems {
 	my $namespace = shift;
 	my $tag = shift;
 	my $message = shift;
 	my $eng = getNamespaceItems($namespace);
 	my $lang = getNamespaceItems($namespace,$languageId);
 	$lang->{$tag}{message} = $message;
 	$lang->{$tag}{lastUpdated} = time();
    # Get rid of $VAR1 prefix
    local $Data::Dumper::Terse = 1;
    local $Data::Dumper::SortKeys = 1;
 	my $output = Dumper $lang;
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
         if (open(FILE,">".$filepath)) {
         	print FILE $content;
         	close(FILE);
 	} else {
 		print "ERROR writing file ".$filepath." because ".$!.".\n";
 		exit;
 	}
 }
 
 #------------------------------------------------------
sub writeLanguage {
 	my $data = shift;
	my $translit_replaces_r = shift;
 	my $output = "package WebGUI::i18n::".$languageId.";\n\n";
 	$output .= "use strict;\n";
 	$output .= "use utf8;\n\n";
 	$output .= "our \$LANGUAGE = {\n";
 	$output .= $data;
 	$output .= "};\n\n";
 
 $translit_replaces_r =~ s/\r//g; # For ***nix OS
 
 	$output .= qq(sub makeUrlCompliant {
         my \$value = shift;\n); 
 $output .= "##<-- start transliteration -->##\n".$translit_replaces_r."\n##<-- end transliteration -->##\n";
 $output .= qq(
 	    \$value =~ s/\\s+\$//;                     #removes trailing whitespace
         \$value =~ s/^\\s+//;                     #removes leading whitespace
         \$value =~ s/^\\\\//;                      #removes leading slash
         \$value =~ s/ /-/g;                      #replaces whitespace with underscores
         \$value =~ s/\\.\$//;                      #removes trailing period
         \$value =~ s/[^A-Za-z0-9\\-\\.\\_\\/]//g;    #removes all funky characters
         \$value =~ s/^\\///;                      #removes a preceeding /
         \$value =~ s/\\/\\//\\//g;                  #removes double /
         return \$value;
 });
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
	chdir($outputPath);
	my $out = `cd $outputPath;/usr/bin/svn update $languageId`;
	my $rawChanges = `cd $outputPath;/usr/bin/svn status $languageId`;
	my @changes = split m{\n}, $rawChanges;
	foreach my $change (@changes) {
		my ($type, $file) = split m{\s+}, $change;
		if ($type eq "?") {
			print "Adding ".$file."<br />";
			system("cd $outputPath;/usr/bin/svn add $file");
		} elsif ($type eq "M") {
			print "Updating ".$file."<br />";
		}
	}
	return '<br /><pre>'.`cd $outputPath;/usr/bin/svn -m update_from_translation_server commit $languageId`.'</pre>';
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
		&bull; <a href="'.buildURL("commitTranslation").'" target="editor">Commit to SVN</a><br />
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
		my $percent = ($total > 0) ? sprintf('%.0f',(($total - $ood) / $total)*100) : 0;
 		$output .= '<tr><td class="'.(($percent == 0) ? 'undefined' : ($percent < 100) ? 'outOfDate' : 'allGood').'">'.$percent.'%</td><td><a href="'.buildURL("listItemsInNamespace",{namespace=>$namespace}).'" target="editor">'.$namespace.'</a></td><td>'.($total - $ood).'/'.$total.'</td></tr>';
 	}
	$output .= '</table>';
 	return $output;
 }
 
 #------------------------------------------------------
sub www_editItem {
 	my $eng = getNamespaceItems($cgi->param("namespace"));
 	my $lang = getNamespaceItems($cgi->param("namespace"),$languageId);
 
 	my $output = '<table width="95%"><form name="editor_on"><tr><th>Visual editor</th><td><input type="radio" name="editor_on" value="0"';
 if (!$editor_on == 1) {$output .= ' checked';} else {$output .= " onClick=\"window.location.href='".buildURL("editItem",{namespace=>$cgi->param("namespace"),tag=>$cgi->param("tag"),is_editor_on=>'0'})."'\"";}
 	$output .= '>&nbsp;On&nbsp;&nbsp;/&nbsp;<input type="radio" name="editor_on" value="1"';
 if ($editor_on == 1) {$output .= ' checked';} else {$output .= " onClick=\"window.location.href='".buildURL("editItem",{namespace=>$cgi->param("namespace"),tag=>$cgi->param("tag"),is_editor_on=>'1'})."'\"";}
 	$output .= '>&nbsp;Off&nbsp;</td></tr></form>';
 	$output .= '<form method="post" action="/#'.$cgi->param("tag").'">';
 	$output .= '<tr><th>Namespace</th><td>'.$cgi->param("namespace").'</td></tr>';
 	$output .= '<input type="hidden" name="languageId" value="'.$languageId.'">';
 	$output .= '<input type="hidden" name="namespace" value="'.$cgi->param("namespace").'">';
 	$output .= '<tr><th>Tag</th><td>'.$cgi->param("tag").'</td></tr>';
 	$output .= '<input type="hidden" name="tag" value="'.$cgi->param("tag").'">';
 	$output .= '<input type="hidden" name="op" value="editItemSave">';
 	$output .= '<tr><th valign="top">Message</td><td width="95%"><textarea style="width: 100%" rows="30" name="message" mce_editable="true">'.fixFormData($lang->{$cgi->param("tag")}{message}).'</textarea></td></tr>';
 	$output .= '<tr><th></th><td><input type="submit" value="Save"></td></tr>';
 	$output .= '<tr><th valign="top">Original Message</th><td>'.$eng->{$cgi->param("tag")}{message}.'</td></tr>';
 	$output .= '<tr><th valign="top">Message Context Info</th><td>'.$eng->{$cgi->param("tag")}{context}.'</td></tr>' if ($eng->{$cgi->param("tag")}{context});
 	$output .= qq(</form></table>);
 	return $output;
 }
 
 #------------------------------------------------------
sub www_editItemSave {
 	setNamespaceItems($cgi->param("namespace"),$cgi->param("tag"),$cgi->param("message"));
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
 	$output .= '<tr><th>Replaces for transliteration<br /><br />Something like:<br /><br />';
 	$output .= '
         $value =~ s/Йа/J\\\'a/;<br />
         $value =~ s/йа/j\\\'a/;<br />
         $value =~ s/ЙА/J\\\'A/;<br />
         $value =~ s/Я/Ja/g;<br />
         $value =~ s/я/ja/g;<br />
 <br />
         $value =~ s/^\\s+//;<br />
         $value =~ s/^\\\\//;<br />
         $value =~ s/ /_/g;<br />
         $value =~ s/\\.\$//;<br />
         $value =~ s/[^A-Za-z0-9\\-\\.\\_\\/]//g;<br />
         $value =~ s/^\\///;<br />
         $value =~ s/\\/\\//\\//g;<br />
 ';
  	$output .= '</th><td width="100%"><textarea style="width: 100%;" rows="20" name="translit_replaces">'.ReadTranslit ().'</textarea><br />Transliterations are used in making URLs and file names conform to a usable standard. URLs and file names often can\'t deal with special characters used by various non-English languages. As such, those characters need to be transliterated into English characters.</td></tr>';
 	$output .= '<tr><th></th><td><input type="submit" value="Save"></td></tr>';
 	$output .= '</table></form>';
 	return $output;
 }
 
 #------------------------------------------------------
sub www_editLanguageSave {
 	setLanguage($cgi->param("label"), $cgi->param("toolbar"), $cgi->param("translit_replaces"), $cgi->param("languageAbbreviation"), $cgi->param("locale"));
 	return "Language saved.<p>".www_editLanguage();
 }

#------------------------------------------------------
sub www_exportTranslation {
	if (languageIdIsBad()) {
		return '';
	}
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
	open (my $notesFile, "<", $outputPath.'/'.$languageId.'/notes.txt');
	my $notes = join("\n", <$notesFile>);
	close($notesFile);
 	my $output = '<form method="post"><table width="95%">';
 	$output .= '<input type="hidden" name="languageId" value="'.$languageId.'">';
 	$output .= '<input type="hidden" name="op" value="translatorsNotesSave">';
  	$output .= '<th></th><td width="100%"><textarea style="width: 100%;" rows="40" name="notes">'.$notes.'</textarea><br />Place any notes of interest here including common dictionary terms, translation notes, and a list of people who worked on this translation. This text will go into the translation distribution, but will not be displayed anywhere on the site, or affect system performance.</td></tr>';
 	$output .= '<tr><th></th><td><input type="submit" value="Save"></td></tr>';
 	$output .= '</table></form>';
 	return $output;
 }
 
 #------------------------------------------------------
sub www_translatorsNotesSave {
	open(my $notesFile, ">", $outputPath.'/'.$languageId.'/notes.txt');
	print {$notesFile} $cgi->param("notes")."\n";
	close($notesFile);
 	return "Notes saved.<p>".www_translatorsNotes();
 }

#------------------------------------------------------
sub ReadTranslit {
 my $translit_replaces_read = '';
 open(TRANSLIT,"$outputPath/$languageId/$languageId.pm") || die "$!\n";
 my @translit = <TRANSLIT>;
    close(TRANSLIT);
 my $flag_T = 0;
 foreach  my $translit (@translit) {
 if ($translit =~ /##<-- end transliteration -->##/) {$flag_T = 0;}
 if ($flag_T == 1) {
 $translit_replaces_read .= $translit;
 }
 if ($translit =~ /##<-- start transliteration -->##/) {$flag_T = 1;}
 }
 return $translit_replaces_read;
 }
 
 #------------------------------------------------------
sub ConvertToUTF {
 
 # Read list of files
 chdir ("$outputPath/$languageId/$languageId/");
    my @files = <*>;
 my $files_l;
 foreach my $file (@files) {
 open(FILE,"./$file") || die "$!\n"; 
   my @files_l = <FILE>;
    close(FILE);
 my $lang_char = "UTF-8";
 $lang_char =~ s/windows-1251/CP1251/g;
 $lang_char =~ s/windows-1252/CP1252/g;
 my $converter = Text::Iconv->new("$lang_char", "UTF-8");
 @files_l = $converter->convert("@files_l");
 
    open(FILE,">$file") || die "$!\n";
    print FILE "@files_l";
    close(FILE);
 $files_l = '';
 	}
 }
