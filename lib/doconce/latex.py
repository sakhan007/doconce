# -*- coding: iso-8859-15 -*-

import os, commands, re, sys, glob, shutil
from common import plain_exercise, table_analysis, \
     _CODE_BLOCK, _MATH_BLOCK, doconce_exercise_output, indent_lines, \
     online_python_tutor, envir_delimiter_lines, safe_join, \
     insert_code_and_tex, is_file_or_url, chapter_pattern
from misc import option, _abort, replace_code_command
additional_packages = ''  # comma-sep. list of packages for \usepackage{}

include_numbering_of_exercises = True

def underscore_in_code(m):
    """For pattern r'\\code\{(.*?)\}', insert \_ for _ in group 1."""
    text = m.group(1)
    text = text.replace('_', r'\_')
    return r'\code{%s}' % text

def get_bib_index_pages():
    bib_page = idx_page = '9999'
    from doconce import dofile_basename
    name = dofile_basename + '.aux'
    if not os.path.isfile(name):
        return bib_page, idx_page

    aux = open(name, 'r')
    lines = aux.readlines()
    aux.close()
    for line in lines:
        if '{References}' in line or '{Bibliography}' in line:
            bib_page = line.split('}{')[-2]
        if '{Index}' in line:
            idx_page = line.split('}{')[-2]
    return bib_page, idx_page

# Mappings from DocOnce code environments to Pygments and lstlisting names
envir2pyg = dict(
    pyshell='python',
    py='python', cy='cython', f='fortran',
    c='c', cpp='c++', sh='bash', rst='rst',
    m ='matlab', pl='perl', swig='c++',
    latex='latex', html='html', js='js',
    java='java',
    xml='xml', rb='ruby', sys='console',
    dat='text', txt='text', csv='text',
    ipy='ipy', do='doconce',
    # pyopt and pysc are treated explicitly
    )
envir2lst = dict(
    pyshell='Python',
    py='Python', cy='Python', f='Fortran',
    c='C', cpp='C++', sh='bash', rst='text',
    m ='Matlab', pl='Perl', swig='C++',
    latex='TeX', html='HTML', js='Java',
    java='Java',
    xml='XML', rb='Ruby', sys='bash',
    dat='text', txt='text', csv='text',
    ipy='Python', do='text',
    # pyopt and pysc are treated explicitly
    )

def latex_code_envir(
    envir,
    envir_spec,
    ):
    leftmargin = option('latex_code_leftmargin=', '2')

    envir2 = envir if envir in envir_spec else 'default'

    package = envir_spec[envir2]['package']
    background = envir_spec[envir2]['background']
    # Default styles
    lst_style = 'style=simple,xleftmargin=%smm' % leftmargin
    vrb_style = 'numbers=none,fontsize=\\fontsize{9pt}{9pt},baselinestretch=0.95,xleftmargin=%smm' % leftmargin
    # mathescape can be used with minted and lstlisting
    # see http://tex.stackexchange.com/questions/149710/how-to-write-math-symbols-in-a-verbatim, minted can only have math in comments within the code
    # but mathescape make problems with bash and $#
    # (can perhaps be fixed with escapechar=... but I haven't found out)
    if envir != 'sh':
        pyg_style = 'fontsize=\\fontsize{9pt}{9pt},linenos=false,mathescape,baselinestretch=1.0,fontfamily=tt,xleftmargin=%smm' % leftmargin
    else:
        pyg_style = 'fontsize=\\fontsize{9pt}{9pt},linenos=false,baselinestretch=1.0,fontfamily=tt,xleftmargin=%smm' % leftmargin
    if envir_spec[envir2]['style'] is not None:
        # Override default style
        if package == 'lst':
            lst_style = envir_spec[envir2]['style']
        if package == 'vrb':
            vrb_style = envir_spec[envir2]['style']
        if package == 'pyg':
            pyg_style = envir_spec[envir2]['style']

    envir_tp = ''
    if envir.endswith('pro'):
        envir_tp = 'pro'
        envir = envir[:-3]
    elif envir.endswith('cod'):
        envir_tp = 'cod'
        envir = envir[:-3]

    from common import get_legal_pygments_lexers
    global envir2pyg, envir2lst

    if envir in ('ipy', 'do'):
        # Find substitutes for ipy and doconce if these lexers
        # are not installed
        # (third-party repos, does not come with pygments, but
        # warnings have been issued by doconce format, with
        # URLs to where the code can be obtained)
        from pygments.lexers import get_lexer_by_name
        try:
            get_lexer_by_name('ipy')
        except:
            envir2pyg['ipy'] = 'python'
        try:
            get_lexer_by_name('doconce')
        except:
            envir2pyg['do'] = 'text'

    if package == 'pyg':
        begin = '\\begin{minted}[%s]{%s}' % (pyg_style, envir2pyg.get(envir, 'text'))
        end = '\\end{minted}'
    elif package == 'lst':
        if envir2lst.get(envir, 'text') == 'text':
            begin = '\\begin{lstlisting}[language=Python,%s]' % (lst_style, )
        else:
            begin = '\\begin{lstlisting}[language=%s,%s]' % (envir2lst.get(envir, 'text'), lst_style)
        end = '\\end{lstlisting}'
    else:
        begin = '\\begin{Verbatim}[%s]' % vrb_style
        end = '\\end{Verbatim}'

    if background != 'white':
        if envir_tp == 'pro':
            begin = '\\begin{pro}{cbg_%s}{bar_%s}' % (background, background) + begin
            if package == 'vrb':
                end = end + '\n\\end{pro}\n\\noindent'
            else:
                end = end + '\\end{pro}\n\\noindent'
        else:
            begin = '\\begin{cod}{cbg_%s}' % background + begin
            if package == 'vrb':
                end = end + '\n\\end{cod}\n\\noindent'
            else:
                end = end + '\\end{cod}\n\\noindent'
    return begin, end

def interpret_latex_code_style():
    latex_code_style = option('latex_code_style=', None)
    if latex_code_style is None:
        return None

    def interpret(text):
        # Extract style parameters inside []
        m = re.search(r'\[(.+?)\]', text)
        if m:
            style = m.group(1)
            text = text.replace('[%s]' % style, '')
        else:
            style = None
        # Find background, if specified
        if '-' in text:
            pkg, bg = text.split('-')
        else:
            bg = 'white'
            pkg = text
        # Strip off envir if present
        if ':' in pkg:
            envir, pkg = pkg.split(':')
        return pkg, bg, style

    legal_envirs = 'pro pypro cypro cpppro cpro fpro plpro shpro mpro cod pycod cycod cppcod ccod fcod plcod shcod mcod rst cppans pyans fans bashans swigans uflans sni dat dsni sys slin ipy pyshell rpy plin ver warn rule summ ccq cc ccl txt htmlcod htmlpro html rbpro rbcod rb xmlpro xmlcod xml latexpro latexcod latex default'.split()
    d = {}
    if '@' not in latex_code_style:
        # Common definition for all languages
        pkg, bg, style = interpret(latex_code_style)
        d['default'] = dict(package=pkg, background=bg, style=style)
    else:
        parts = latex_code_style.split('@')
        for part in parts:
            if not ':' in part:
                print '*** error: wrong syntax in --latex_code_style= specification'
                _abort()
            envir, spec = part.split(':')
            if envir not in legal_envirs:
                print '*** warning: not registered code environment "%s"' % envir
            pkg, bg, style = interpret(spec)
            d[envir] = dict(package=pkg, background=bg, style=style)
    if 'default' not in d:
        # Use Verbatim as default
        d['default'] = dict(package='vrb', background='white', style=None)

    return d


def latex_code_lstlisting(latex_code_style):
    s = ''  # Resulting latex code
    s += r"""
% Common lstlisting parameters
\lstset{
  basicstyle=\small \ttfamily,
  breaklines=false,          % break/wrap lines
  breakatwhitespace=true,    % let linebreaks happen at whitespace
  breakindent=40pt,
  tab=,
  tabsize=4,                 % tab means 4 spaces
  %belowskip=\smallskipamount,  % space between code and text below
  xleftmargin=5pt,           % indentation of code frame
  xrightmargin=5pt,
  framexleftmargin=5pt,      % add frame space to the left of code
  %numbers=left,             % put line numbers on the left
  %stepnumber=2,             % stepnumber=1 numbers each line, =n every n lines
  %framerule=0.4pt           % thickness of frame
  aboveskip=1ex,
  showstringspaces=false,    % show spaces in strings with a particular underscore
  showspaces=false,          % show spaces with a particular underscore
  showtabs=false,
  keepspaces=true,
  columns=fullflexible,      % tighter character kerning, like verb
  escapeinside={||},         % for |\pause| in slides and math in code blocks
  extendedchars=\true,       % allows non-ascii chars, does not work with utf-8
}

% Styles for lstlisting
"""
    styles = dict(
       simple=r"""
\lstdefinestyle{simple}{
commentstyle={},
}
""",
       redblue=r"""
\lstdefinestyle{redblue}{
keywordstyle=\color{blue}\bfseries,
commentstyle=\color{myteal},
stringstyle=\color{darkgreen},
identifierstyle=\color{darkorange},
}
""",
       yellow2_fb=r"""
% Use this one without additional background color
\lstdefinestyle{yellow2_fb}{         % approx same colors as in the FEniCS book
frame=trbl,                          % top+right+bottom+left (tb draws double lines at top + bottom)
rulecolor=\color{black},             % frame color
backgroundcolor=\color{yellow!10},
keywordstyle=\color{blue}\bfseries,
commentstyle=\color{comment_green}\slshape,
stringstyle=\color{string_red},
identifierstyle=\color{darkorange},
}
""",
       blue1=r"""
% Use this one without additional background color
\lstdefinestyle{blue1}{              % blue1 background for code snippets
backgroundcolor=\color{cbg_blue1},
%keywordstyle=\color{blue}\bfseries,
%commentstyle=\color{comment_green}\slshape,
%stringstyle=\color{string_red},
%identifierstyle=\color{darkorange},
%columns=fullflexible,  % tighter character kerning, like verb
}
""",
        blue1bar="""
% Use this one without additional background color
% (same as blue1, but with bar_blue1 frame)
\lstdefinestyle{blue1bar}{           % blue1 background for complete programs
backgroundcolor=\color{cbg_blue1},
frame=trbl,                          % top+right+bottom+left (tb draws double lines at top + bottom)
rulecolor=\color{bar_blue1},         % frame color
%keywordstyle=\color{blue}\bfseries,
%commentstyle=\color{comment_green}\slshape,
%stringstyle=\color{string_red},
%identifierstyle=\color{darkorange},
%columns=fullflexible,  % tighter character kerning, like verb
}
""",
       gray=r"""
% Use this one without additional background color
\lstdefinestyle{gray}{
backgroundcolor=\color{cbg_gray},
%frame=trbl,                           % top+right+bottom+left (tb draws double lines at top + bottom)
%framerule=0.4pt                      % thickness of frame
rulecolor=\color{black!40},           % frame color
}
""",
        graybar="""
% Use this one without additional background color
\lstdefinestyle{graybar}{
backgroundcolor=\color{cbg_gray},
frame=trbl,                           % top+right+bottom+left (tb draws double lines at top + bottom)
rulecolor=\color{bar_gray1},          % frame color
%framerule=0.4pt                      % thickness of frame
}
""",
        graycolor=r"""
% Use this one without additional background color
\lstdefinestyle{graycolor}{
backgroundcolor=\color{cbg_gray},
%frame=trbl,                           % top+right+bottom+left (tb draws double lines at top + bottom)
%framerule=0.4pt                      % thickness of frame
keywordstyle=\color{keyword_pink}\bfseries,
commentstyle=\color{comment_green}\slshape,
stringstyle=\color{string_red},
identifierstyle=\color{darkorange},
}
""",
        garycolorbar="""
% Use this one without additional background color
\lstdefinestyle{graycolorbar}{
backgroundcolor=\color{cbg_gray},
frame=trbl,                           % top+right+bottom+left (tb draws double lines at top + bottom)
rulecolor=\color{bar_gray1},          % frame color
%framerule=0.4pt                      % thickness of frame
keywordstyle=\color{keyword_pink}\bfseries,
commentstyle=\color{comment_green}\slshape,
stringstyle=\color{string_red},
identifierstyle=\color{darkorange},
}
""",
        )

    # Just write styles for the ones that are requested
    requested_styles = re.findall(r'style=([A-Za-z0-9:_]+)[,\]]',
                                  latex_code_style)
    if 'simple' not in requested_styles:
        requested_styles.append('simple')
    for style in requested_styles:
        s += styles[style]
    s += """
% end of custom lstdefinestyles
"""
    filename = option('latex_code_lststyles=', None)
    if filename is not None:
        # User has specified additional lst styles
        if os.path.isfile(filename):
            text = open(filename, 'r').read()
            s += text
        else:
            print '*** error: file "%s" does not exist' % filename
            _abort()

    return s

def latex_code(filestr, code_blocks, code_block_types,
               tex_blocks, format):

    if option('latex_double_hyphen'):
        print '*** warning: --latex_double_hyphen may lead to unwanted edits.'
        print '             search for all -- in the .p.tex file and check.'
        # Replace - by -- in some cases for nicer LaTeX look of hyphens:
        # Note: really dangerous for inline mathematics: $kx-wt$.
        from_to = [
            # equation refs
            (r'(\(ref\{.+?\}\))-(\(ref\{.+?\}\))', r'\g<1>--\g<2>'),
            # like Navier-Stokes, but not `Q-1`
            (r'([^$`\\/{!][A-Za-z]{2,})-([^\\/{][A-Za-z]{2,}[^`$/}])', r'\g<1>--\g<2>'),
            # single - at end of line
            (r' +-$', ' --'),
            # single - at beginning of line
            (r'^ *- +', ' -- '),
                   ]
        for pattern, replacement in from_to:
            filestr = re.sub(pattern, replacement, filestr, flags=re.MULTILINE)


    # Note: cannot fix double quotes right here for it destroys
    # preprocess/mako code too. Instead we had to introduce the LaTeX
    # style for quotes: ``[A-Za-z][A-Za-z0-9 ]*?''
    # The re.sub are really dangerous with a lot of side effects. They
    # are still here as a warning of never adding such functionality!
    #filestr = re.sub(r'([^\\])"([^"]+?)"', r"""\g<1>``\g<2>''""", filestr)
    # Drop fixing of single quotes - it interferes with the double quotes fix,
    # and it might lead to strange results for the apostrophe!
    #NO: filestr = re.sub(r"""'([^']+?)'""", r"""`\g<1>'""", filestr)

    # References to external documents (done before !bc blocks in
    # case such blocks explain the syntax of the external doc. feature)
    pattern = r'^%\s*[Ee]xternaldocuments?:\s*(.+)$'
    m = re.search(pattern, filestr, re.MULTILINE)
    #filestr = re.sub(pattern, '', filestr, flags=re.MULTILINE)
    if m:
        commands = [r'\externaldocument{%s}' % name.strip()
                    for name in m.group(1).split(',')]
        new_text = r"""

%% References to labels in external documents:
\usepackage{xr}
%s

%% insert custom LaTeX commands...
""" % ('\n'.join(commands))
        filestr = filestr.replace('% insert custom LaTeX commands...', new_text)
        # Check that the files exist
        for name in m.group(1).split(','):
            name2 = name.strip() + '.aux'
            if not os.path.isfile(name2):
                print '\n*** warning: need external file %s,' % name2
                print '    but it does not exist (compile latex/pdflatex!)'
                name2 = name + '.do.txt'
                if not os.path.isfile(name2):
                    print '*** error: external document %s listed in # Externaldocuments does not exist' % name2
                    _abort()

    # labels inside tex envirs must have backslash \label:
    for i in range(len(tex_blocks)):
        tex_blocks[i] = re.sub(r'([^\\])label', r'\g<1>\\label',
                               tex_blocks[i])

    lines = filestr.splitlines()
    # Add Online Python Tutor URL before code blocks with pyoptpro code
    for i in range(len(lines)):
        if _CODE_BLOCK in lines[i]:
            words = lines[i].split()
            n = int(words[0])
            if len(words) >= 3 and words[2] == 'pyoptpro' and \
                       not option('device=', '') == 'paper':
                # Insert an Online Python Tutor link and add to lines[i]
                post = '\n\\noindent\n(\\href{{%s}}{Visualize execution}) ' % \
                       online_python_tutor(code_blocks[n], return_tp='url')
                lines[i] = lines[i].replace(' pyoptpro', ' pypro') + post + '\n'

    filestr = safe_join(lines, '\n')
    filestr = insert_code_and_tex(filestr, code_blocks, tex_blocks, format)

    filestr = re.sub(r'^!bt\n', '', filestr, flags=re.MULTILINE)
    filestr = re.sub(r'!et\n', '', filestr)

    # Check for misspellings
    envirs = 'pro pypro cypro cpppro cpro fpro plpro shpro mpro cod pycod cycod cppcod ccod fcod plcod shcod mcod htmlcod htmlpro latexcod latexpro rstcod rstpro xmlcod xmlpro cppans pyans fans bashans swigans uflans sni dat dsni csv txt sys slin ipy rpy plin ver warn rule summ ccq cc ccl pyshell pyoptpro pyscpro ipy do'.split()
    from common import has_custom_pygments_lexer, get_legal_pygments_lexers
    if 'ipy' in code_block_types:
        has_custom_pygments_lexer('ipy')
    if 'do' in code_block_types:
        has_custom_pygments_lexer('doconce')
    envirs += get_legal_pygments_lexers()
    for envir in code_block_types:
        if envir and not envir.endswith('hid'):
            if envir[-1].isdigit():
                # strip off digit that can occur inside admons if the
                # option --latex_admon_envir_map=X is used
                envir = envir[:-1]
            if envir not in envirs:
                print 'Warning: found "!bc %s", but %s is not a standard predefined ptex2tex environment' % (envir, envir)

    # --- Final fixes for latex format ---

    latex_style = option('latex_style=', 'std')

    chapters = True if re.search(r'\\chapter\{', filestr) is not None else False

    # \texttt{>>>} gives very strange typesetting in the Springer book,
    # but not in ordinary latex, so we need to fix that with hack back
    # to \code{>>>}
    filestr = filestr.replace(r'\texttt{>>>}', r'\Verb!>>>!')

    # Remove "Appendix: " from headings in appendices
    appendix_pattern = r'\\(chapter|section\*?)\{Appendix:\s+'
    filestr = re.sub(appendix_pattern,
                     '\n\n\\\\appendix\n\n' + r'\\\g<1>{', filestr,  # the first
                     count=1)
    filestr = re.sub(appendix_pattern, r'\\\g<1>{', filestr) # all others

    # Replace all admon envirs by block envirs in case of beamer.
    if option('latex_title_layout=', '') == 'beamer':
        # The admon envir is paragraph if beamer. Replace all such envirs
        # with the beamer block envir. (This is more robus for the admon
        # title than previous solution where we redefined all admon envirs
        # to be block envirs.)
        admons = 'notice', 'summary', 'warning', 'question', 'block'
        Admons = [admon[0].upper() + admon[1:] for admon in admons]
        for admon in admons:
            # First admons without title
            pattern = r'!b%s *\n' % admon
            filestr = re.sub(pattern, r'\\begin{block}{%s}\n' %
                             ('' if admon == 'block' else
                              admon[0].upper() + admon[1:]), filestr)
            # Admons with title and fontsize spec.
            pattern = r'!b%s +\((.+?)\) +(.*)' % admon
            filestr = re.sub(pattern, lambda m: '\\begin{block}{%s }\n' %
                             m.group(2) + ('\\footnotesize\n'
                                           if m.group(1) == 'small'
                                           else '\\large\n'), filestr)
            # Admons with fontsize spec. and no title
            pattern = r'!b%s +\((.+?)\)' % admon
            filestr = re.sub(pattern, lambda m: '\\begin{block}{%s}\n' %
                             ('' if admon == 'block' else
                              admon[0].upper() + admon[1:]) +
                             ('\\footnotesize\n' if m.group(1) == 'small'
                              else '\\large\n'), filestr)
            # Admons with title
            pattern = r'!b%s +(.+)' % admon
            filestr = re.sub(pattern, r'\\begin{block}{\g<1> }', filestr)
            pattern = r'!e%s' % admon
            filestr = re.sub(pattern, r'\end{block}', filestr)
    # Fix None titles to empty titles
    filestr = filestr.replace('begin{block}{None }', 'begin{block}{}')
    # Fix % inside verbatim in block/paragraph titles
    pattern = r'(begin\{block\}|paragraph)\{.*?\\code\{.*?%.*?\}'
    filestr = re.sub(pattern, lambda m: m.group().replace('%', '\\%'), filestr)

    # Make sure exercises are surrounded by \begin{doconceexercise} and
    # \end{doconceexercise} with some exercise counter
    #comment_pattern = INLINE_TAGS_SUBST[format]['comment'] # only in doconce.py
    comment_pattern = '%% %s'
    pattern = comment_pattern % envir_delimiter_lines['exercise'][0] + '\n'

    if latex_style == 'Springer_lnup':
        replacement = pattern
    else:
        replacement = pattern + r"""\begin{doconceexercise}
\refstepcounter{doconceexercisecounter}
"""

    filestr = filestr.replace(pattern, replacement)
    pattern = comment_pattern % envir_delimiter_lines['exercise'][1] + '\n'
    if latex_style != 'Springer_lnup':
        replacement = r'\end{doconceexercise}' + '\n' + pattern
    else:
        replacement = r'\end{exercise}' + '\n' + pattern
    filestr = filestr.replace(pattern, replacement)

    if include_numbering_of_exercises:
        # Remove section numbers of exercise sections
        if option('examples_as_exercises'):
            exercise_pattern = r'subsection\*?\{(Exercise|Problem|Project|Example) +(\d+)\s*: +(.+\})'
        else:
            exercise_pattern = r'subsection\*?\{(Exercise|Problem|Project) +(\d+)\s*: +(.+\})'
        # Make table of contents or list of exercises entry
        # (might have to add \phantomsection right before because
        # of the hyperref package?)
#        filestr, n = re.subn(exercise_pattern,
#                         r"""subsection*{\g<1> \g<2>: \g<3>
# % table of contents with exercises:
#\\addcontentsline{toc}{subsection}{\g<2>: \g<3>
# % separate list of exercises:
#\\addcontentsline{loe}{doconceexercise}{\g<1> \g<2>: \g<3>
#""", filestr)
        exercise_headings = re.findall(exercise_pattern, filestr)
        if exercise_headings:
            if option('latex_list_of_exercises=', 'none') == 'none':
                if latex_style == 'Springer_lnup':
                    filestr = re.sub(exercise_pattern,
        r"""begin{exercise}{\g<3>
""", filestr)
                else:
                    filestr = re.sub(exercise_pattern,
        r"""subsection*{\g<1> \\thedoconceexercisecounter: \g<3>
""", filestr)
            elif option('latex_list_of_exercises=', 'none') == 'toc':
                filestr = re.sub(exercise_pattern,
        r"""subsection*{\g<1> \\thedoconceexercisecounter: \g<3>
\\addcontentsline{toc}{subsection}{\\thedoconceexercisecounter: \g<3>
""", filestr)
            elif option('latex_list_of_exercises=', 'none') == 'loe':
                 filestr = re.sub(exercise_pattern,
        r"""subsection*{\g<1> \\thedoconceexercisecounter: \g<3>
\\addcontentsline{loe}{doconceexercise}{\g<1> \\thedoconceexercisecounter: \g<3>
""", filestr)
            # Treat {Exercise}/{Project}/{Problem}
            # Pattern starts with --- begin exercise ... \subsection{
            # but not \addcontentsline
            exercise_pattern = r'^% --- begin exercise ---\n\\begin\{doconceexercise\}\n\\refstepcounter\{doconceexercisecounter\}\n\n\\subsection\{(.+?)$(?!\\addcont)'
            # No increment of exercise counter, but add to contents
            replacement = r"""% --- begin exercise ---
\begin{doconceexercise}

\subsection{\g<1>"""
            if option('latex_list_of_exercises=', 'none') != 'none':
                replacement += r"""
\addcontentsline{loe}{doconceexercise}{\g<1>
"""
            replacement = fix_latex_command_regex(replacement, 'replacement')
            filestr = re.sub(exercise_pattern, replacement, filestr,
                             flags=re.MULTILINE)
            # Find suitable titles for list of exercises
            import sets
            types_of_exer = sets.Set()
            for exer_tp, dummy, dummy in exercise_headings:
                types_of_exer.add(exer_tp)
            types_of_exer = list(types_of_exer)
            types_of_exer = ['%ss' % tp for tp in types_of_exer]  # plural
            types_of_exer = [tp for tp in sorted(types_of_exer)]  # alphabetic order
            if len(types_of_exer) == 1:
                types_of_exer = types_of_exer[0]
            elif len(types_of_exer) == 2:
                types_of_exer = ' and '.join(types_of_exer)
            elif len(types_of_exer) > 2:
                types_of_exer[-1] = 'and ' + types_of_exer[-1]
                types_of_exer = ', '.join(types_of_exer)
            heading = "List of %s" % types_of_exer
            # Insert definition of \listofexercises
            if r'\tableofcontents' in filestr:
                # Here we take fragments normally found in a stylefile
                # and put them in the .text file, which requires
                # \makeatletter, \makeatother, etc, see
                # http://www.tex.ac.uk/cgi-bin/texfaq2html?label=atsigns
                # Also, the name of the doconce exercise environment
                # cannot be doconce:exercise (previous name), but
                # must be doconceexercise because of the \l@... command
                if chapters:
                    style_listofexercises = r"""
%% --- begin definition of \listofexercises command ---
\makeatletter
\newcommand\listofexercises{
\chapter*{%(heading)s
          \@mkboth{%(heading)s}{%(heading)s}}
\markboth{%(heading)s}{%(heading)s}
\@starttoc{loe}
}
\newcommand*{\l@doconceexercise}{\@dottedtocline{0}{0pt}{6.5em}}
\makeatother
%% --- end definition of \listofexercises command ---
""" % vars()
                    insert_listofexercises = r"""
\clearemptydoublepage
\listofexercises
\clearemptydoublepage
""" % vars()
                else:
                    style_listofexercises = r"""
%% --- begin definition of \listofexercises command ---
\makeatletter
\newcommand\listofexercises{\section*{%(heading)s}
\@starttoc{loe}
}
\newcommand*{\l@doconceexercise}{\@dottedtocline{0}{0pt}{6.5em}}
\makeatother
%% --- end definition of \listofexercises command ---
""" % vars()
                    insert_listofexercises = r"""
\listofexercises
""" % vars()
                target = r'\newcounter{doconceexercisecounter}'
                filestr = filestr.replace(
                    target, target + style_listofexercises)
                if option('latex_list_of_exercises=', 'none') == 'loe':
                    target = r'\tableofcontents'
                    filestr = filestr.replace(
                        target, target + insert_listofexercises)
    if latex_style != 'Springer_lnup':
        # Subexercise headings should utilize \subex{} and not plain \paragraph{}
        subex_header_postfix = option('latex_subex_header_postfix=', ')')
        # Default is a), b), but could be a:, b:, or a. b.
        filestr = re.sub(r'\\paragraph\{([a-z])\)\}',
                     r'\subex{\g<1>%s}' % subex_header_postfix,
                     filestr)

    # Avoid Filename: as a new paragraph with indentation
    filestr = re.sub(r'^(Filenames?): +?\\code\{',
                     r'\\noindent \g<1>: \code{', filestr,
                     flags=re.MULTILINE)

    # Preface is normally an unnumbered section or chapter
    # (add \markboth only if book style with chapters
    if chapters:
        markboth = r'\n\markboth{\g<2>}{\g<2>}'
    else:
        markboth = ''
    filestr = re.sub(r'(section|chapter)\{(Preface.*)\}',
                     r'\g<1>*{\g<2>}' + markboth, filestr)

    # Fix % and # in link texts (-> \%, \# - % is otherwise a comment...)
    pattern = r'\\href\{\{(.+?)\}\}\{(.+?)\}'
    def subst(m):  # m is match object
        url = m.group(1).strip()
        text = m.group(2).strip()
        # fix % without backslash
        text = re.sub(r'([^\\])\%', r'\g<1>\\%', text)
        text = re.sub(r'([^\\])\#', r'\g<1>\\#', text)
        return '\\href{{%s}}{%s}' % (url, text)
    filestr = re.sub(pattern, subst, filestr, flags=re.DOTALL)

    if option('device=', '') == 'paper':
        # Make adjustments for printed versions of the PDF document.
        # Fix links so that the complete URL is in a footnote

        no_footnote = option('latex_no_program_footnotelink')
        suffices = ['.py', '.f', '.f90', '.f95', '.c', '.cpp', '.cxx',
                    '.m', '.r', '.js', '.tex', '.h']

        def subst(m):  # m is match object
            url = m.group(1).strip()
            text = m.group(2).strip()
            #print 'url:', url, 'text:', text
            #if not ('ftp:' in text or 'http' in text or '\\nolinkurl{' in text):
            if not ('ftp:' in text or 'http' in text):
                # The link text does not display the URL so we include it
                # in a footnote (\nolinkurl{} indicates URL: "...")
                texttt_url = url.replace('_', '\\_').replace('#', '\\#').replace('%', '\\%').replace('&', '\\&')
                # use \protect\footnote such that hyperlinks works within
                # captions and other places (works well outside too with \protect)
                # (doesn't seem necessary - footnotes in captions are a
                # a bad thing since figures are floating)

                return_str = '\\href{{%s}}{%s}' % (url, text) + \
                             '\\footnote{\\texttt{%s}}' % texttt_url
                # See if we shall drop the footnote for programs
                if text.startswith(r'\nolinkurl{') and no_footnote:
                    for suffix in suffices:
                        if url.endswith(suffix):
                            return_str = '\\href{{%s}}{%s}' % (url, text)
                            break
                return return_str
            else: # no substitution, URL is in the link text
                return '\\href{{%s}}{%s}' % (url, text)
        filestr = re.sub(pattern, subst, filestr, flags=re.DOTALL)

    # \code{} in section headings and paragraph needs a \protect
    pattern = r'^(\\.*?section\*?|\\paragraph)\{(.+)\}'  # (no .+? - must go to the last }!)
    headings = re.findall(pattern, filestr, flags=re.MULTILINE)

    for tp, heading in headings:
        if '\\code{' in heading:
            new_heading = re.sub(r'\\code\{(.*?)\}', underscore_in_code,
                                 heading)
            new_heading = new_heading.replace(r'\code{', r'\protect\code{')
            # Fix double }} for code ending (\section{...\code{...}})
            new_heading = re.sub(r'code\{(.*?)\}$', r'code{\g<1>} ',
                                 new_heading)
            filestr = filestr.replace(r'%s{%s}' % (tp, heading),
                                      r'%s{%s}' % (tp, new_heading))
    # Headings in paragraph versions of admons also need \protect\code
    pattern = r'^(!b[a-z]+ +)(.*)$'
    headings = re.findall(pattern, filestr, flags=re.MULTILINE)
    for tp, heading in headings:
        if '\\code{' in heading:
            new_heading = re.sub(r'\\code\{(.*?)\}', underscore_in_code,
                                 heading)
            new_heading = new_heading.replace(r'\code{', r'\protect\code{')
            filestr = filestr.replace(r'%s%s' % (tp, heading),
                                      r'%s%s' % (tp, new_heading))

    # addcontentsline also needs \protect\code
    addcontentslines = re.findall(r'^(\\addcontentsline\{.+)$', filestr,
                                  flags=re.MULTILINE)
    for line in addcontentslines:
        if '\\code{' in line:
            new_line = line.replace(r'\code{', r'\protect\code{')
            filestr = filestr.replace(line, new_line)
    # paragraphadmon also needs \protect\Verb

    if latex_style == 'elsevier':
        filestr = filestr.replace(r'\title{', r"""\begin{frontmatter}

\title{""", 1)
        if r'\end{keyword}' in filestr:
            filestr = filestr.replace(r'\end{keyword}', r"""\end{keyword}

\end{frontmatter}

%\linenumbers
""", 1)
        elif r'\end{abstract}' in filestr:
            filestr = filestr.replace(r'\end{abstract}', r"""\end{abstract}

\end{frontmatter}

%\linenumbers
""", 1)
        filestr = re.sub(r'^\bibliographystyle{.+?}', r'\bibliographystyle{elsarticle-num}', filestr, flags=re.MULTILINE)
        # Remove date
        filestr = re.sub(r'\\begin\{center\} % date.+?\\end\{center\}', '',
                         filestr, flags=re.DOTALL)
        filestr = filestr.replace(r'\tableofcontents', r'%\tableofcontents')
    elif latex_style.startswith('siam'):
        filestr = re.sub(r'^\bibliographystyle{.+?}', r'\bibliographystyle{siam}', filestr, flags=re.MULTILINE)
        filestr = filestr.replace(r'\tableofcontents', r'%\tableofcontents  % not legal in SIAM latex style')
        # Remove date
        filestr = re.sub(r'\\begin\{center\} % date.+?\\end\{center\}', '',
                         filestr, flags=re.DOTALL)


    if option('section_numbering=', 'on') == 'off':
        filestr = filestr.replace('section{', 'section*{')

    # Support for |\pause| in slides to allow for parts of code blocks
    # to pop up
    if r'|\pause|' in filestr:
        if format in ('latex', 'pdflatex'):
            if '\\begin{minted}' in filestr:
                filestr = re.sub(r'^\\begin\{minted\}\[',
                                 r'\\begin{minted}[escapeinside=||,',
                                 filestr, flags=re.MULTILINE)

    # Translate to .tex or .p.tex format

    latex_code_style = interpret_latex_code_style()

    filestr = replace_code_command(filestr)  # subst \code{...}

    # Fix footnotes `verbatim`[^footnote] (originally without space)
    # (this forced 3 extra spaces in latex_footnotes)
    filestr = re.sub(r'([!?@|}])   \\footnote{', r'\g<1>\\footnote{', filestr)

    lines = filestr.splitlines()
    current_code_envir = None
    for i in range(len(lines)):
        if lines[i].startswith('!bc'):
            words = lines[i].split()
            if len(words) == 1:
                current_code_envir = 'ccq'
            else:
                if words[1] in ('pyoptpro', 'pyscpro'):
                    current_code_envir = 'pypro'
                else:
                    current_code_envir = words[1]
            if current_code_envir is None:
                # Should not happen since a !bc is encountered first and
                # current_code_envir is then set above
                # There should have been checks for this in doconce.py
                print '*** error: mismatch between !bc and !ec'
                print '\n'.join(lines[i-3:i+4])
                _abort()
            if latex_code_style is None:
                lines[i] = '\\b' + current_code_envir
            else:
                begin, end = latex_code_envir(current_code_envir,
                                              latex_code_style)
                lines [i] = begin
        if lines[i].startswith('!ec'):
            if current_code_envir is None:
                # No envir set by previous !bc?
                print '*** error: mismatch between !bc and !ec'
                print '    check that every !bc matches !ec in the following text:'
                print filestr
                _abort()
            if latex_code_style is None:
                lines[i] = '\\e' + current_code_envir
            else:
                begin, end = latex_code_envir(current_code_envir,
                                              latex_code_style)
                lines [i] = end
            current_code_envir = None
    filestr = safe_join(lines, '\n')

    return filestr

def latex_figure(m, includegraphics=True):
    filename = m.group('filename')
    basename  = os.path.basename(filename)
    stem, ext = os.path.splitext(basename)

    # Figure on the web?
    if filename.startswith('http'):
        this_dir = os.getcwd()
        figdir = 'downloaded_figures'
        if not os.path.isdir(figdir):
            os.mkdir(figdir)
        os.chdir(figdir)
        if is_file_or_url(filename) != 'url':
            print '*** error: cannot fetch latex figure %s on the net (no connection or invalid URL)' % filename
            _abort()
        import urllib
        f = urllib.urlopen(filename)
        file_content = f.read()
        f.close()
        f = open(basename, 'w')
        f.write(file_content)
        f.close()
        filename = os.path.join(figdir, basename)
        os.chdir(this_dir)

    #root, ext = os.path.splitext(filename)
    # doconce.py ensures that images are transformed to .ps or .eps

    # note that label{...} are substituted by \label{...} (inline
    # label tag) so we write just label and not \label below:

    # fraction is 0.9/linewidth by default, but can be adjusted with
    # the fraction keyword
    frac = 0.9
    sidecaption = 0
    opts = m.group('options')
    if opts:
        info = [s.split('=') for s in opts.split()]
        for opt, value in info:
            if opt == 'frac':
                frac = float(value)
        for opt, value in info:
            if opt == 'sidecap':
                sidecaption = 1

    if includegraphics:
        if sidecaption == 1:
            includeline = r'\includegraphics[width=%s\linewidth]{%s}' % (frac, filename)
        else:
            includeline = r'\centerline{\includegraphics[width=%s\linewidth]{%s}}' % (frac, filename)
    else:
        includeline = r'\centerline{\psfig{figure=%s,width=%s\linewidth}}' % (filename, frac)

    caption = m.group('caption').strip()
    m = re.search(r'label\{(.+?)\}', caption)
    if m:
        label = m.group(1).strip()
    else:
        label = ''

    # URLs that become footnotes pose problems inside a caption.
    # It is not recommended to have footnotes in floats (safe solutions
    # require minipage).
    if option('device=', '') == 'paper':
        pattern = r'".+?"\s*:\s*"https?:.+?"'
        links = re.findall(pattern, caption, flags=re.DOTALL)
        if links:
            print '*** error: hyperlinks inside caption pose problems for'
            print '    latex output and --device=paper because they lead'
            print '    to footnotes in captions. (Footnotes in floats require'
            print '    minipage.) The latex document with compile with'
            print '    \\protect\\footnote, but the footnote is not shown.'
            print '    Recommendation: rewrite caption.\n'
            print '-----------\n', caption, '\n-----------\n'
            _abort()

    # `verbatim_text` in backquotes is translated to \code{verbatim\_text}
    # which then becomes \Verb!verbatim\_text! when running ptex2tex or
    # doconce ptex2tex, but this command also needs a \protect inside a caption
    # (besides the escaped underscore).
    # (\Verb requires the fancyvrb package.)
    # Alternative: translate `verbatim_text` to {\rm\texttt{verbatim\_text}}.
    verbatim_handler = 'Verb'  # alternative: 'texttt'
    verbatim_text = re.findall(r'(`[^`]+?`)', caption)
    verbatim_text_new = []
    for words in verbatim_text:
        new_words = words
        if '_' in new_words:
            new_words = new_words.replace('_', r'\_')
        if verbatim_handler == 'Verb':
            new_words = '\\protect ' + new_words
        elif verbatim_handler == 'texttt':
            # Replace backquotes by {\rm\texttt{}}
            new_words = r'{\rm\texttt{' + new_words[1:-1] + '}}'
        # else: do nothing
        verbatim_text_new.append(new_words)
    for from_, to_ in zip(verbatim_text, verbatim_text_new):
        caption = caption.replace(from_, to_)
    if sidecaption == 1:
        includeline='\sidecaption[t] ' + includeline
    if caption:
        result = r"""
\begin{figure}[t]
  %s
  \caption{
  %s
  }
\end{figure}
%%\clearpage %% flush figures %s
""" % (includeline, caption, label)
    else:
        # drop caption and place figure inline
        result = r"""
\begin{center}  %% inline figure
  %s
\end{center}
""" % (includeline)
        result = r"""

%% inline figure
%s

""" % (includeline)
    return result

def latex_movie(m):
    filename = m.group('filename')
    caption = m.group('caption').strip()

    if 'youtu.be' in filename:
        filename = filename.replace('youtu.be', 'youtube.com')

    def link_to_local_html_movie_player():
        """Simple solution where an HTML file is made for playing the movie."""
        from common import default_movie
        text = default_movie(m)

        # URL to HTML viewer file must have absolute path in \href
        html_viewer_file_pattern = \
             r'(.+?) `(.+?)`: load "`(.+?)`": "(.+?)" into a browser'
        m2 = re.search(html_viewer_file_pattern, text)
        if m2:
            html_viewer_file = m2.group(4)
            if os.path.isfile(html_viewer_file):
                html_viewer_file_abs = os.path.abspath(html_viewer_file)
                text = text.replace(': "%s"' % html_viewer_file,
                                    ': "file://%s"' % html_viewer_file_abs)
        return '\n' + text + '\n'

    movie = option('latex_movie=', 'href')
    controls = option('latex_movie_controls=', 'on')
    # Do not typeset movies in figure environments since DocOnce documents
    # assume inline movies
    text = r"""
\begin{doconce:movie}
\refstepcounter{doconce:movie:counter}
\begin{center}"""
    if 'youtube.com' in filename:
        if movie == 'media9':
            text += r"""
\includemedia[
width=0.6\linewidth,height=0.45\linewidth,
activate=pageopen,
flashvars={
modestbranding=1   %% no YouTube logo in control bar
&autohide=1        %% controlbar autohide
&showinfo=0        %% no title and other info before start
&rel=0             %% no related videos after end
},
]{}{%(filename)s}
""" % vars()
        else:
            # Just a link
            text += r"""
"`%(filename)s`": "%(filename)s"
""" % vars()
    elif 'vimeo.com' in filename:
        # Can only provide a link to the Vimeo movie
        # Rename embedded files to ordinary Vimeo URL
        filename = filename.replace('http://player.vimeo.com/video',
                                    'http://vimeo.com')
        text += '"`%(filename)s`": "%(filename)s"' % vars()
    elif '*' in filename or '->' in filename:
        # Filename generator
        # frame_*.png
        # frame_%04d.png:0->120
        # http://some.net/files/frame_%04d.png:0->120
        if filename.startswith('http'):
            # Cannot handle animation of frames on the web,
            # make a separate html file that can play the animation
            text += link_to_local_html_movie_player()
        else:
            import DocWriter
            header, jscode, form, footer, frames = \
                    DocWriter.html_movie(filename)
            # Make a good estimate of the frame rate: it takes 30 secs
            # to run the animation: rate*30 = no of frames
            framerate = int(len(frames)/30.)
            commands = [r'\includegraphics[width=0.9\textwidth]{%s}' %
                        f for f in frames]
            commands = ('\n\\newframe\n').join(commands)
            # Note: cannot use animategraphics because it cannot handle
            # filenames on the form frame_%04d.png, only frame_%d.png.
            # Expand all plotfile names instead.
            text += r"""
\begin{animateinline}[controls,loop]{%d} %% frames: %s -> %s
%s
\end{animateinline}
""" % (framerate, frames[0], frames[-1], commands)
    else:
        # Local movie file or URL (all the methods below handle
        # either local files or URLs)

        label = filename.replace('/', '').replace('.', '').replace('-','')
        stem, ext = os.path.splitext(filename)

        if movie == 'multimedia':
            text += r"""
%% Beamer-style \movie command
\movie[
showcontrols,
label=%(filename)s,
width=0.9\linewidth,
autostart]{\nolinkurl{%(filename)s}}{%(filename)s}
""" % vars()
        elif movie not in ('media9', 'movie15'):
            if filename.startswith('http'):
                # Just plain link
                text += r"""
%% link to web movie
\href{%(filename)s}{\nolinkurl{%(filename)s}}
""" % vars()
            else:
                # \href{run:localfile}{linktext}
                text += r"""
%% link to external viewer
\href{run:%(filename)s}{\nolinkurl{%(filename)s}}
""" % vars()
        elif movie == 'media9':
            if ext.lower() in ('.mp4', '.flv'):
                text += r"""
%% media9 package
\includemedia[
label=%(label)s,
width=0.8\linewidth,
activate=pageopen,         %% or onclick or pagevisible
addresource=%(filename)s,  %% embed the video in the PDF
flashvars={
source=%(filename)s
&autoPlay=true
&loop=true
&scaleMode=letterbox       %% preserve aspect ratio while scaling this video
}]{}{VPlayer.swf}
""" % vars()
                if controls:
                    text += r"""%%\mediabutton[mediacommand=%(label)s:playPause]{\fbox{\strut Play/Pause}}
""" % vars()
            elif ext.lower() in ('.mp3',):
                text += r"""
%% media9 package
\includemedia[
label=%(label)s,
addresource=%(filename)s,  %% embed the video in the PDF
flashvars={
source=%(filename)s
&autoPlay=true
},
transparent
]{\framebox[0.5\linewidth[c]{\nolinkurl{%(filename)s}}}{APlayer9.swf}
""" % vars()
            elif ext.lower() in ('.mpg', '.mpeg', '.avi'):
                # Use old movie15 package which will launch a separate player
                external_viewer = option('latex_external_movie_viewer')
                external = '\nexternalviewer,' if external_viewer else ''
                text += r"""
%% movie15 package
\includemovie[poster,
label=%(label)s,
autoplay,
controls,
toolbar,%(external)s
text={\small (Loading %(filename)s)},
repeat,
]{0.9\linewidth}{0.9\linewidth}{%(filename)s}
""" % vars()
                if not external_viewer:
                    text += r"""
\movieref[rate=0.5]{%(label)s}{Slower}
\movieref[rate=2]{%(label)s}{Faster}
\movieref[default]{%(label)s}{Normal}
\movieref[pause]{%(label)s}{Play/Pause}
\movieref[stop]{%(label)s}{Stop}
""" % vars()
            else:
                # Use a link for other formats
                if filename.startswith('http'):
                    # Just plain link
                    text += r"""
%% link to web movie
\href{%(filename)s}{\nolinkurl{%(filename)s}}
""" % vars()
                else:
                # \href{run:localfile}{linktext}
                    text += r"""
%% link to external viewer
\href{run:%(filename)s}{\nolinkurl{%(filename)s}}
""" % vars()

        elif movie == 'movie15':
            external_viewer = option('latex_external_movie_viewer')
            external = '\nexternalviewer,' if external_viewer else ''
            text += r"""
%% movie15 package
\includemovie[poster,
label=%(label)s,
autoplay,
controls,
toolbar,%(external)s
%%text={\small (Loading %(filename)s)},
repeat,
]{0.9\linewidth}{0.9\linewidth}{%(filename)s}
""" % vars()
            if not external_viewer:
                text += r"""
\movieref[rate=0.5]{%(label)s}{Slower}
\movieref[rate=2]{%(label)s}{Faster}
\movieref[default]{%(label)s}{Normal}
\movieref[pause]{%(label)s}{Play/Pause}
\movieref[stop]{%(label)s}{Stop}
""" % vars()

    text += '\\end{center}\n'
    if caption:
        text += r"""
\begin{center}  %% movie caption
Movie \arabic{doconce:movie:counter}: %s
\end{center}
""" % caption
    text += '\\end{doconce:movie}\n'
    return text

def latex_linebreak(m):
    text = m.group('text')
    if text:
        return '%s\\\\' % text
    else:
        # no text, use \vspace instead
        return '\n\n\\vspace{3mm}\n\n'

def latex_footnotes(filestr, format, pattern_def, pattern_footnote):
    # Collect all footnote definitions in a dict (for insertion in \footnote{})
    footnotes = {name: text for name, text, dummy in
                 re.findall(pattern_def, filestr, flags=re.MULTILINE|re.DOTALL)}
    # Remove definitions
    filestr = re.sub(pattern_def, '', filestr, flags=re.MULTILINE|re.DOTALL)

    def subst_footnote(m):
        name = m.group('name')
        space = m.group('space')
        lookbehind = m.group(1)
        try:
            text = footnotes[name].strip()
        except KeyError:
            print '*** error: definition of footnote with name "%s"' % name
            print '    has no corresponding footnote [^%s]' % name
            _abort()
        # Make the footnote on one line in case it appears in lists
        # (newline will then end the list)
        text = ' '.join(text.splitlines())

        if lookbehind in ('`', '_',) and space == '':
            # Inline verbatim: need extra space for the inline verbatim subst
            # to work (fixed later in latex_code fix part)
            space = '   '  # 3 spaces to be recognized for later subst to ''
        return '%s\\footnote{%s}' % (space, text)

    filestr = re.sub(pattern_footnote, subst_footnote, filestr)
    return filestr

def latex_table(table):
    latex_table_format = option('latex_table_format=', 'quote')
    if latex_table_format == 'left':
        table_align = ('', '')
    elif latex_table_format == 'quote':
        table_align = (r'\begin{quote}', r'\end{quote}')
    elif latex_table_format == 'center':
        table_align = (r'\begin{center}', r'\end{center}')
    elif latex_table_format == 'footnotesize':
        table_align = (r'{\footnotesize', r'}')
    elif latex_table_format == 'tiny':
        table_align = (r'{\tiny', r'}')
    latex_style = option('latex_style=', 'std')

    column_width = table_analysis(table['rows'])

    #ncolumns = max(len(row) for row in table['rows'])
    ncolumns = len(column_width)
    #import pprint; pprint.pprint(table)
    column_spec = table.get('columns_align', 'c'*ncolumns)
    column_spec = column_spec.replace('|', '')
    if len(column_spec) != ncolumns:  # (allow | separators)
        print 'Table has column alignment specification: %s, but %d columns' \
              % (column_spec, ncolumns)
        print 'Table with rows', table['rows']
        _abort()

    # we do not support | in headings alignments (could be fixed,
    # by making column_spec not a string but a list so the
    # right elements are picked in the zip-based loop)
    heading_spec = table.get('headings_align', 'c'*ncolumns)#.replace('|', '')
    if len(heading_spec) != ncolumns:
        print 'Table has headings alignment specification: %s, '\
              'but %d columns' % (heading_spec, ncolumns)
        print 'Table with rows', table['rows']
        _abort()

    s = '\n' + table_align[0] + '\n'
    if latex_style == "Springer_T2":
        s += '{\\small   % Springer T2 style: small table font and more vspace\n\n\\vspace{4mm}\n\n'
    s += r'\begin{tabular}{%s}' % column_spec + '\n'
    for i, row in enumerate(table['rows']):
        if row == ['horizontal rule']:
            s += r'\hline' + '\n'
        else:
            # check if this is a headline between two horizontal rules:
            if i == 1 and \
               table['rows'][i-1] == ['horizontal rule'] and \
               table['rows'][i+1] == ['horizontal rule']:
                headline = True
                # Empty column headings?
                skip_headline = max([len(column.strip())
                                     for column in row]) == 0
            else:
                headline = False

            if headline:
                if skip_headline:
                    row = []
                else:
                    # First fix verbatim inside multicolumn
                    # (recall that doconce.py table preparations
                    # translates `...` to \code{...})
                    verbatim_pattern = r'code\{(.+?)\}'
                    for i in range(len(row)):
                        m = re.search(verbatim_pattern, row[i])
                        if m:
                            #row[i] = re.sub(verbatim_pattern,
                            #                r'texttt{%s}' % m.group(1),
                            #                row[i])
                            # (\code translates to \Verb, which is allowed here)

                            row[i] = re.sub(
                                r'\\code\{(.*?)\}', underscore_in_code, row[i])

                    row = [r'\multicolumn{1}{%s}{ %s }' % (a, r) \
                           for r, a in zip(row, heading_spec)]
            else:
                row = [r.ljust(w) for r, w in zip(row, column_width)]

            s += ' & '.join(row) + ' \\\\\n'

    s += r'\end{tabular}' + '\n'
    if latex_style == "Springer_T2":
        s += '\n\\vspace{4mm}\n\n}\n'
    s += table_align[1] + '\n\n' + r'\noindent' + '\n'
    return s

def latex_title(m):
    title = m.group('subst')
    short_title = option('short_title=', title)
    if short_title != title:
        short_title_cmd = '[' + short_title + ']'
    else:
        short_title_cmd = ''

    # Acknowledgment/reference associated with the title?
    ackn = option('latex_title_reference=', None)
    if ackn is not None:
        title += r'\footnote{%s}' % ackn

    text = ''
    latex_style = option('latex_style=', 'std')
    title_layout = option('latex_title_layout=', 'doconce_heading')
    section_headings = option('latex_section_headings=', 'std')

    if latex_style in ("Springer_T2", "Springer_lncse", "Springer_lnup"):
        text += r"""
\frontmatter
\setcounter{page}{3}
\pagestyle{headings}
"""
    elif latex_style in ("Springer_lncse"):
        text += r"""
% With hyperref loaded, \contentsline needs 3 args
%\contentsline{chapter}{Bibliography}{829}{chapter.Bib}
%\contentsline{chapter}{Index}{831}{chapter.Index}
"""
    text += """

% ----------------- title -------------------------
"""
    if title_layout == "std" or \
           latex_style in ('siamltex', 'siamltexmm', 'elsevier','Springer_lnup'):
        if section_headings in ("blue", "strongblue"):
            text += r"""
\title%(short_title_cmd)s{{\color{seccolor} %(title)s}}
""" % vars()
        else:
            text += r"""
\title%(short_title_cmd)s{%(title)s}
""" % vars()
    elif title_layout == "titlepage":
        text += r"""
\thispagestyle{empty}
\hbox{\ \ }
\vfill
\begin{center}
{\huge{\bfseries{
\begin{spacing}{1.25}"""
        if section_headings in ("blue", "strongblue"):
            text += r"""
{\color{seccolor}\rule{\linewidth}{0.5mm}} \\[0.4cm]
{\color{seccolor}%(title)s}
\\[0.4cm] {\color{seccolor}\rule{\linewidth}{0.5mm}} \\[1.5cm]""" % vars()
        else:
            text += r"""
{\rule{\linewidth}{0.5mm}} \\[0.4cm]
{%(title)s}
\\[0.4cm] {\rule{\linewidth}{0.5mm}} \\[1.5cm]""" % vars()
        text += r"""
\end{spacing}
}}}
"""
    elif title_layout == "Springer_collection":
        # No blue section here since style here is governed by Springer
        text += r"""
\title*{%(title)s}
%% Short version of title:
\titlerunning{%(short_title)s}
""" % vars()
    elif title_layout == "beamer":
        text += r"""
\title%(short_title_cmd)s{%(title)s}
""" % vars()
    else:
        if section_headings in ("blue", "strongblue"):
            text += r"""
\thispagestyle{empty}

\begin{center}
{\LARGE\bf
\begin{spacing}{1.25}
{\color{seccolor} %(title)s}
\end{spacing}
}
\end{center}
""" % vars()
        else:
            text += r"""
\thispagestyle{empty}

\begin{center}
{\LARGE\bf
\begin{spacing}{1.25}
%(title)s
\end{spacing}
}
\end{center}
""" % vars()
    return text

def latex_author(authors_and_institutions, auth2index,
                 inst2index, index2inst, auth2email):

    def email(author, prefix='', parenthesis=True):
        address = auth2email[author]
        if address is None:
            email_text = ''
        else:
            if parenthesis:
                lp, rp = '(', ')'
            else:
                lp, rp = '', ''
            address = address.replace('_', r'\_')
            name, place = address.split('@')
            #email_text = r'%s %s\texttt{%s} at \texttt{%s}%s' % (prefix, lp, name, place, rp)
            email_text = r'%s %s\texttt{%s@%s}%s' % \
                         (prefix, lp, name, place, rp)
        return email_text

    one_author_at_one_institution = False
    if len(auth2index) == 1:
        author = list(auth2index.keys())[0]
        if len(auth2index[author]) == 1:
            one_author_at_one_institution = True

    text = """

% ----------------- author(s) -------------------------
"""
    title_layout = option('latex_title_layout=', 'doconce_heading')
    latex_style = option('latex_style=', 'std')

    if title_layout == 'std' or latex_style in ('siamltex', 'siamltexmm','Springer_lnup'):
        # Traditional latex heading
        text += r"""
\author{"""
        footnote = 'thanks' if latex_style.startswith('siam') else 'footnote'
        author_command = []
        for a, i, e in authors_and_institutions:
            a_text = a
            e_text = email(a, prefix='Email:', parenthesis=False)
            if i is not None:
                a_text += r'\%s{' % footnote
                if len(i) == 1:
                    i_text = i[0]
                elif len(i) == 2:
                    i_text = ' and '.join(i)
                else:
                    i[-1] = 'and ' + i[-1]
                    i_text = '; '.join(i)
                if e_text:
                    a_text += e_text + '. ' + i_text
                else:
                    a_text += i_text
                if not a_text.endswith('.'):
                    a_text += '.'
                a_text += '}'
            else: # Just email
                if e_text:
                    a_text += r'\%s{%s.}' % (footnote, e_text)
            author_command.append(a_text)
        author_command = '\n\\and '.join(author_command)

        text += author_command + '}\n'

    elif title_layout == 'titlepage':
        text += r"""
\vspace{1.3cm}
"""
        if one_author_at_one_institution:
            author = list(auth2index.keys())[0]
            email_text = email(author)
            text += r"""
{\Large\textsf{%s%s}}\\ [3mm]
""" % (author, email_text)
        else:
            for author in auth2index: # correct order of authors
                email_text = email(author)
                text += r"""
{\Large\textsf{%s${}^{%s}$%s}}\\ [3mm]
""" % (author, str(auth2index[author])[1:-1], email_text)
        text += r"""
\ \\ [2mm]
"""
        if one_author_at_one_institution:
            text += r"""
{\large\textsf{%s} \\ [1.5mm]}""" % (index2inst[1])
        else:
            for index in index2inst:
                text += r"""
{\large\textsf{${}^%d$%s} \\ [1.5mm]}""" % (index, index2inst[index])

    elif title_layout == 'Springer_collection':
        text += r"""
\author{%s}
%% Short version of authors:
%%\authorrunning{...}
""" % (' and ' .join([author for author in auth2index]))

        text += r"\institute{"
        a_list = []
        for a, i, e in authors_and_institutions:
            s = a
            if i is not None:
                s += r'\at ' + ' and '.join(i)
            if e is not None:
                s += r'\email{%s}' % e
            a_list.append(s)
        text += r' \and '.join(a_list) + '}\n'

    elif title_layout == 'beamer':
        text += r"""
\author{"""
        author_command = []
        for a, i, e in authors_and_institutions:
            a_text = a
            inst = r'\inst{' + ','.join([str(i) for i in auth2index[a]]) + '}'
            a_text += inst
            author_command.append(a_text)
        text += '\n\\and\n'.join(author_command) + '}\n'
        inst_command = []
        institutions = [index2inst[i] for i in index2inst]
        text += r'\institute{' + '\n\\and\n'.join(
            [inst + r'\inst{%d}' % (i+1)
             for i, inst in enumerate(institutions)]) + '}'
    elif title_layout == 'doconce_heading' or latex_style == 'elsevier':
        if one_author_at_one_institution:
            author = list(auth2index.keys())[0]
            email_text = email(author)
            if latex_style == 'elsevier':
                text += r"""
\author[inst]{%s}
""" % author
            else:
                text += r"""
\begin{center}
{\bf %s%s}
\end{center}

    """ % (author, email_text)
        else:
            for author in auth2index: # correct order of authors
                email_text = email(author)
                if latex_style == 'elsevier':
                    institutions = ','.join(['inst'+str(i) for i in auth2index[author]])
                    text += r"""
\author[%s]{%s}""" % (institutions, author)
                else:
                    text += r"""
\begin{center}
{\bf %s${}^{%s}$%s} \\ [0mm]
\end{center}

    """ % (author, str(auth2index[author])[1:-1], email_text)

        # Institutions
        if latex_style == 'elsevier':
            if one_author_at_one_institution:
                text += r"""\address[inst]{%s}""" % index2inst[1] + '\n'
            else:
                for index in index2inst:
                    text += r"""\address[inst%d]{%s}""" % \
                            (index, index2inst[index]) + '\n'
        else:
            text += r'\begin{center}' + '\n' + '% List of all institutions:\n'
            if one_author_at_one_institution:
                text += r"""\centerline{{\small %s}}""" % \
                        (index2inst[1]) + '\n'
            else:
                for index in index2inst:
                    text += r"""\centerline{{\small ${}^%d$%s}}""" % \
                            (index, index2inst[index]) + '\n'

            text += r"""\end{center}
    """
    else:
        print '*** error: cannot create author field when'
        print '    --latex_title_layout=%s --latex_style=%s' % (title_layout, latex_style)
        _abort()

    text += """
% ----------------- end author(s) -------------------------

"""
    return text

def latex_date(m):
    title_layout = option('latex_title_layout=', 'doconce_heading')
    date = m.group('subst')
    text = ''
    if title_layout == 'std':
        text += r"""
\date{%(date)s}
\maketitle
""" % vars()
    elif title_layout == 'beamer':
        text += r"""
\date{%(date)s
%% <optional titlepage figure>
}
""" % vars()
    elif title_layout == 'titlepage':
        text += r"""
%% --- begin date ---
\ \\ [10mm]
{\large\textsf{%(date)s}}

\end{center}
%% --- end date ---
\vfill
\clearpage
""" % vars()
    else:  # doconce special heading
        text += r"""
\begin{center} %% date
%(date)s
\end{center}

\vspace{1cm}

""" % vars()
    return text

def latex_abstract(m):
    text = m.group('text').strip()
    rest = m.group('rest')
    title_layout = option('latex_title_layout=', 'doconce_heading')
    abstract = ''
    if title_layout == 'Springer_collection':
        abstract += r"""
\abstract{
%(text)s
}
""" % vars()
    else:
        abstract += r"""
\begin{abstract}
%(text)s
\end{abstract}
""" % vars()
    abstract += '\n%(rest)s' % vars()
    return abstract

def latex_ref_and_label(section_label2title, format, filestr):
    filestr = filestr.replace('label{', r'\label{')
    # add ~\ between chapter/section and the reference
    pattern = r'([Ss]ection|[Cc]hapter)(s?)\s+ref\{'  # no \[A-Za-z] pattern => no fix
    # recall \r is special character so it needs \\r
    # (could call fix_latex_command_regex for the replacement)
    replacement = r'\g<1>\g<2>~\\ref{'
    #filestr = re.sub(pattern, replacement, filestr, flags=re.IGNORECASE)
    cpattern = re.compile(pattern, flags=re.IGNORECASE)
    filestr = cpattern.sub(replacement, filestr)
    # range ref:
    filestr = re.sub(r'-ref\{', r'-\\ref{', filestr)
    # the rest of the ' ref{}' (single refs should have ~ in front):
    filestr = re.sub(r'\s+ref\{', r'~\\ref{', filestr)
    filestr = re.sub(r'\(ref\{', r'(\\ref{', filestr)

    # equations are ok in the doconce markup

    # perform a substitution of "LaTeX" (and ensure \LaTeX is not there):
    filestr = re.sub(fix_latex_command_regex(r'\LaTeX({})?',
                               application='match'), 'LaTeX', filestr)
    #filestr = re.sub('''([^"'`*_A-Za-z0-9-])LaTeX([^"'`*_A-Za-z0-9-])''',
    #                 r'\g<1>{\LaTeX}\g<2>', filestr)
    #filestr = re.sub(r'''([^"'`*/-])\bLaTeX\b([^"'`*/-])''',
    #                 r'\g<1>{\LaTeX}\g<2>', filestr)
    # This one is not good enough for verbatim `LaTeX`:
    #filestr = re.sub(r'\bLaTeX\b', r'{\LaTeX}', filestr)
    non_chars = '''"'`*/_-'''
    filestr = re.sub(r'''([^%s])\bLaTeX\b([^%s])''' % (non_chars, non_chars),
                     r'\g<1>{\LaTeX}\g<2>', filestr)
    filestr = re.sub(r'''([^%s])\bpdfLaTeX\b([^%s])''' % (non_chars, non_chars),
                     fix_latex_command_regex(
                     r'\g<1>\textsc{pdf}{\LaTeX}\g<2>',
                     application='replacement'), filestr)
    filestr = re.sub(r'''([^%s])\bBibTeX\b([^%s])'''% (non_chars, non_chars),
                     fix_latex_command_regex(
                     r'\g<1>\textsc{Bib}\negthinspace{\TeX}\g<2>',
                     application='replacement'), filestr)
    # Fix \idx{{\LaTeX}...} to \idx{LaTeX...} (otherwise all the
    # LaTeX index keywords appear at the beginning because of {)
    filestr = re.sub(r'idx\{\{\\LaTeX\}', r'idx{LaTeX', filestr)
    filestr = re.sub(r'idx\{\\textsc{pdf}\{\\LaTeX\}', r'idx{pdfLaTeX', filestr)
    filestr = re.sub(r'idx\{\\textsc\{Bib\}\\negthinspace\{\\TeX\}', r'idx{BibTeX', filestr)

    # handle & (Texas A&M -> Texas A{\&}M):
    # (NOTE: destroys URLs with & - and potentially align math envirs)
    #filestr = re.sub(r'([A-Za-z])\s*&\s*([A-Za-z])', r'\g<1>{\&}\g<2>', filestr)

    # handle non-English characters:
    chars = {'�': r'{\ae}', '�': r'{\o}', '�': r'{\aa}',
             '�': r'{\AE}', '�': r'{\O}', '�': r'{\AA}',
             }
    # Not implemented
    #for c in chars:
    #    filestr, n = re.subn(c, chars[c], filestr)
    #    print '%d subst of %s' % (n, c)
    #    #filestr = filestr.replace(c, chars[c])

    # Handle "50%" and similar (with initial space, does not work
    # for 50% as first word on a line, so we add a fix for that
    filestr = re.sub(r'( [0-9.]+)%', r'\g<1>\%', filestr)
    filestr = re.sub(r'(^[0-9.]+)%', r'\g<1>\%', filestr, flags=re.MULTILINE)

    # Fix common error et. al. cite{ (et. should be just et)
    filestr = re.sub(r'et\. +al +cite(\{|\[)', r'et al. cite\g<1>', filestr)

    # Fix periods followed by too long space in the following cases
    prefix = r'Prof\.', r'Profs\.', r'prof\.', r'profs\.', r'Dr\.', \
             r'assoc\.', r'Assoc.', r'Assist.', r'Mr\.', r'Ms\.', 'Mss\.', \
             r'Fig\.', r'Tab\.', r'Univ\.', r'Dept\.', r'abbr\.', r'cf\.', \
             r'e\.g\.', r'E\.g\.', r'i\.e\.', r'Approx\.', r'approx\.', \
             r'Exer\.', r'Sec\.', r'Ch\.', r'App\.', r'et al\.', 'no\.', \
             r'vs\.'
    # Avoid r'assist\.' - matches too much
    for p in prefix:
        filestr = re.sub(r'(%s) +([\\A-Za-z0-9$])' % p, r'\g<1>~\g<2>',
                         filestr)

    # Allow C# and F# languages
    # (be careful as it can affect music notation!)
    pattern = r'(^| )([A-Za-z]+)#([,.;:!) ]|$)'
    replacement = r'\g<1>\g<2>\#\g<3>'
    filestr = re.sub(pattern, replacement, filestr, flags=re.MULTILINE)

    # Treat quotes right just before we insert verbatim blocks

    return filestr

def latex_index_bib(filestr, index, citations, pubfile, pubdata):
    # About latex technologies for bib:
    # http://tex.stackexchange.com/questions/25701/bibtex-vs-biber-and-biblatex-vs-natbib
    # May consider moving to biblatex if it is compatible enough.

    #print 'index:', index
    #print 'citations:', citations
    filestr = filestr.replace('cite{', r'\cite{')
    filestr = filestr.replace('cite[', r'\cite[')
    # Fix spaces after . inside cite[] and insert ~
    pattern = r'cite\[(.+?)\. +'
    filestr = re.sub(pattern, r'cite[\g<1>.~', filestr)

    margin_index = option('latex_index_in_margin')

    for word in index:
        pattern = 'idx{%s}' % word
        if '`' in word:
            # Verbatim typesetting (cannot use \Verb!...! in index)
            # Replace first `...` with texttt and ensure right sorting
            word = re.sub(r'^(.*?)`([^`]+?)`(.*)$',  # subst first `...`
            fix_latex_command_regex(r'\g<1>\g<2>@\g<1>{\rm\texttt{\g<2>}}\g<3>',
                                    application='replacement'), word)
            # Subst remaining `...`
            word = re.sub(r'`(.+?)`',  # subst first `...`
            fix_latex_command_regex(r'{\rm\texttt{\g<1>}}',
                                    application='replacement'), word)
            # fix underscores:
            word = word.replace('_', r'\_')

            # fix %
            word = word.replace('%', r'\%')

        replacement = r'\index{%s}' % word

        if margin_index:
            if '!' in word:
                word = word.replace('!', ': ')
            margin = word.split('@')[-1] if '@' in word else word
            replacement += r'\marginpar{\footnotesize %s}' % margin

        filestr = filestr.replace(pattern, replacement)


    if pubfile is not None:
        # Always produce a new bibtex file
        bibtexfile = pubfile[:-3] + 'bib'
        print '\nexporting publish database %s to %s:' % (pubfile, bibtexfile)
        publish_cmd = 'publish export %s' % os.path.basename(bibtexfile)
        # Note: we have to run publish in the directory where pubfile resides
        this_dir = os.getcwd()
        pubfile_dir = os.path.dirname(pubfile)
        if not pubfile_dir:
            pubfile_dir = os.curdir
        os.chdir(pubfile_dir)
        os.system(publish_cmd)
        os.chdir(this_dir)
        # Remove heading right before BIBFILE because latex has its own heading
        pattern = r'={5,9} .+? ={5,9}\s+^BIBFILE'
        filestr = re.sub(pattern, 'BIBFILE', filestr, flags=re.MULTILINE)

        bibstyle = option('latex_bibstyle=', 'plain')
        bibtext = fix_latex_command_regex(r"""

\bibliographystyle{%s}
\bibliography{%s}
""" % (bibstyle, bibtexfile[:-4]), application='replacement')
        if re.search(chapter_pattern, filestr, flags=re.MULTILINE):
            # Let a document with chapters have Bibliography on a new
            # page and in the toc
            bibtext = fix_latex_command_regex(r"""

\clearemptydoublepage
\markboth{Bibliography}{Bibliography}
\thispagestyle{empty}""") + bibtext
            # (the \cleardoublepage might not work well with Koma-script)

        filestr = re.sub(r'^BIBFILE:.+$', bibtext, filestr,
                         flags=re.MULTILINE)
        cpattern = re.compile(r'^BIBFILE:.+$', re.MULTILINE)
        filestr = cpattern.sub(bibtext, filestr)
    return filestr


def latex_exercise(exer):
    return doconce_exercise_output(
           exer,
           include_numbering=include_numbering_of_exercises,
           include_type=include_numbering_of_exercises)

def latex_exercise_old(exer):
    # NOTE: this is the old exercise handler!!
    s = ''  # result string

    # Reuse plain_exercise (std doconce formatting) where possible
    # and just make a few adjustments

    s += exer['heading'] + ' ' + exer['title'] + ' ' + exer['heading'] + '\n'
    if 'label' in exer:
        s += 'label{%s}' % exer['label'] + '\n'
    s += '\n' + exer['text'] + '\n'
    for hint_no in sorted(exer['hint']):
        s += exer['hint'][hint_no] + '\n'
        #s += '\n' + exer['hint'][hint_no] + '\n'
    if 'file' in exer:
        #s += '\n' + r'\noindent' + '\nFilename: ' + r'\code{%s}' % exer['file'] + '\n'
        s += 'Filename: ' + r'\code{%s}' % exer['file'] + '.\n'
    if 'comments' in exer:
        s += '\n' + exer['comments']
    if 'solution' in exer:
        pass
    return s

def latex_box(block, format, text_size='normal'):
    if 'begin{figure}' in block:
        print '*** error: a !bbox-!ebox environment cannot contain a figure with caption.'
        print '    Remove the figure, remove the caption, or remove the box.'
        print '\nBox text:\n', block
        _abort()
    return r"""
\begin{center}
\begin{Sbox}
\begin{minipage}{0.85\linewidth}
%s
\end{minipage}
\end{Sbox}
\fbox{\TheSbox}
\end{center}""" % (block)

def latex_quote(block, format, text_size='normal'):
    return r"""
\begin{quote}
%s
\end{quote}
""" % (block) # no indentation in case block has code

latexfigdir = 'latex_figs'

def _get_admon_figs(filename):
    if filename is None:
        return
    # Extract graphics file from latex_styles.zip, when needed
    # Idea: copy all latex_styles.zip files to a pool, latex_figs.all
    # Copy from latex_figs.all to latex_figs as needed.
    # Remove latex_figs.all at the end of typeset_envirs
    # (cannot do it in latex_code cleanup since typeset_envirs is
    # called after)
    datafile = 'latex_styles.zip'
    latexfigdir_all = latexfigdir + '.all'
    if not os.path.isdir(latexfigdir_all):
        os.mkdir(latexfigdir_all)
        os.chdir(latexfigdir_all)
        import doconce
        doconce_dir = os.path.dirname(doconce.__file__)
        doconce_datafile = os.path.join(doconce_dir, datafile)
        #print 'copying admon figures from %s to subdirectory %s' % \
        #      (doconce_datafile, latexfigdir)
        shutil.copy(doconce_datafile, os.curdir)
        import zipfile
        zipfile.ZipFile(datafile).extractall()
        os.remove(datafile)
        os.chdir(os.pardir)
    if not os.path.isdir(latexfigdir):
        os.mkdir(latexfigdir)
        print '*** made directory %s for admon figures' % latexfigdir
    if not os.path.isfile(os.path.join(latexfigdir, filename)):
        shutil.copy(os.path.join(latexfigdir_all, filename), latexfigdir)

_admon_latex_figs = dict(
    grayicon=dict(
        warning='small_gray_warning',
        question='small_gray_question2',  # 'small_gray_question3'
        notice='small_gray_notice',
        summary='small_gray_summary',
        ),
    yellowicon=dict(
        warning='small_yellow_warning',
        question='small_yellow_question',
        notice='small_yellow_notice',
        summary='small_yellow_summary',
        ),
    )

def get_admon_figname(admon_tp, admon_name):
    if admon_tp in _admon_latex_figs:
        if admon_name in _admon_latex_figs[admon_tp]:
            return _admon_latex_figs[admon_tp][admon_name]
        else:
            return None
    else:
        if admon_name in ('notice', 'warning', 'summary', 'question'):
            return admon_name
        else:
            return None

admons = 'notice', 'summary', 'warning', 'question', 'block'
for _admon in admons:
    _Admon = _admon.capitalize()
    _title_period = '' if option('latex_admon_title_no_period') else '.'
    text = r"""
def latex_%(_admon)s(text_block, format, title='%(_Admon)s', text_size='normal'):
    if title.lower().strip() == 'none':
        title = ''
    if title == 'Block':  # block admon has no default title
        title = ''

    code_envir_transform = option('latex_admon_envir_map=', None)
    if code_envir_transform:
        envirs = re.findall(r'^\\b([A-Za-z0-9_]+)$', text_block, flags=re.MULTILINE)
        import sets
        envirs = list(sets.Set(envirs))  # remove multiple items
        if code_envir_transform.isdigit():
            _envir_mapping = {}
            # Just append the digit(s)
            for envir in envirs:
                _envir_mapping[envir] = envir + code_envir_transform
        else:
            # Individual mapping for each possible envir
            _envir_mapping = dict([pair.split('-') for pair in code_envir_transform.split(',')])
        for envir in envirs:
            text_block = re.sub(r'\\(b|e)%%s' %% envir,
            r'\\\g<1>%%s' %% _envir_mapping.get(envir, envir), text_block)


    latex_admon = option('latex_admon=', 'mdfbox')
    if option('latex_title_layout=', '') == 'beamer':
        latex_admon = 'paragraph'  # block environ will be used anyway

    if text_size == 'small':
        # When a font size changing command is used, incl a \par at the end
        text_block = r'{\footnotesize ' + text_block + '\n\\par}'
        # Add reduced initial vertical space?
        if latex_admon in ("yellowicon", "grayicon", "colors2"):
            text_block = r'\vspace{-2.5mm}\par\noindent' + '\n' + text_block
        elif latex_admon == "colors1":
            # Add reduced initial vertical space
            text_block = r'\vspace{-3.5mm}\par\noindent' + '\n' + text_block
        elif latex_admon in ("mdfbox", "graybox2"):
            text_block = r'\vspace{0.5mm}\par\noindent' + '\n' + text_block
    elif text_size == 'large':
        text_block = r'{\large ' + text_block + '\n\\par}'
        title = r'{\large ' + title + '}'

    # title in mdfbox (or graybox2 with mdframed) cannot handle , or []
    title_mdframed = title   # potentially modified title for mdframed package
    if latex_admon == 'mdfbox' or \
        (latex_admon =='graybox2' and '%(_admon)s' != 'summary'):
        for char in ',[]':
            if char in title_mdframed:
                print '*** error: character "%%s" is not legal in %(_admon)s admon title:' %% char
                print '   "%%s"' %% title
                print '    for --latex_admon=%%s' %% latex_admon
                if char == ',':
                    print '    see if you can replace , by "and" or a dash...'
                print '    (the character will simply be removed if you override the abortion)'
                _abort()
                title_mdframed = title_mdframed.replace(char, '')
        if '%%' in title_mdframed:  # must be escaped
            title_mdframed = title_mdframed.replace('%%', r'\%%')
    if title_mdframed and title_mdframed[-1] not in ('.', ':', '!', '?'):
        title_mdframed += '%(_title_period)s'
    if latex_admon in ('mdfbox',):
        title = title_mdframed

    # For graybox2 we use graybox2admon except for summary without verbatim code,
    # then \grayboxhrules is used (which can be wrapped in a small box of 50 percent
    # with in the text for A4 format)
    grayboxhrules = False
    text_block_graybox2 = text_block
    title_graybox2 = title
    if '%(_admon)s' == 'summary':
        if title != 'Summary':
            if title_graybox2 and title_graybox2[-1] not in ('.', '!', '?', ';', ':'):
                title_graybox2 += ':'
            text_block_graybox2 = r'\textbf{%%s} ' %% title_graybox2 + text_block_graybox2
        # else: no title if title == 'Summary' for graybox2
        # Any code in text_block_graybox2? If so, cannot use \grayboxhrules
        m1 = re.search(r'^\\(b|e).*(cod|pro)', text_block_graybox2, flags=re.MULTILINE)
        m2 = '\\code{' in text_block_graybox2
        if m1 or m2:
            grayboxhrules = False
        else:
            grayboxhrules = True

    if grayboxhrules:
        # summary admon without any code
        envir_graybox2 = r'''\grayboxhrules{
%%s
}''' %% text_block_graybox2
    else:
        # same mdframed package as for mdfbox admon, use modified title_mdframed
        envir_graybox2 = r'''
\begin{graybox2admon}[%%s]
%%s
\end{graybox2admon}

''' %% (title_mdframed, text_block_graybox2)

    if latex_admon in ('colors1', 'colors2', 'mdfbox', 'grayicon', 'yellowicon'):
        text = r'''
\begin{%(_admon)s_%%(latex_admon)sadmon}[%%(title)s]
%%(text_block)s
\end{%(_admon)s_%%(latex_admon)sadmon}

''' %% vars()
        figname = get_admon_figname(latex_admon, '%(_admon)s')
        if figname is not None:
            if format == 'pdflatex':
                figname += '.pdf'
            elif format == 'latex':
                figname += '.eps'
            _get_admon_figs(figname)
    elif latex_admon == 'paragraph':
        if title and title[-1] not in ('.', ':', '!', '?'):
            title += '%(_title_period)s'
        if '%%' in title:
            title = title.replace('%%', '\\%%')
        text = r'''
%%%% --- begin paragraph admon ---
\paragraph{%%(title)s}
%%(text_block)s
%%%% --- end paragraph admon ---

''' %% vars()

    elif latex_admon == 'graybox2':
        text = r'''
%%(envir_graybox2)s
''' %% vars()
    else:
        print '*** error: illegal --latex_admon=%%s' %% latex_admon
        print '    valid styles are colors1, colors2, mdfbox, graybox2,'
        print '    grayicon, yellowicon, and paragraph.'
        _abort()

    return text
    """ % vars()
    exec(text)



def _latex_admonition_old_does_not_work_with_verbatim(
    admon, admon_name, figname, rgb):
    if isinstance(rgb[0], (float,int)):
        rgb = [str(v) for v in rgb]
    text = '''
def latex_%s(block, format, title='%s'):
    ext = '.eps' if format == 'latex' else '.pdf'
    _get_admon_figs('%s' + ext)
    return r"""

\definecolor{%sbackground}{rgb}{%s}
\setlength{\\fboxrule}{2pt}
\\begin{center}
\\fcolorbox{black}{%sbackground}{
\\begin{minipage}{0.8\\textwidth}
\includegraphics[height=0.3in]{%s/%s%%s}
\ \ \ {\large\sc %%s}\\\\ [3mm]
%%s
\end{minipage}}
\end{center}
\setlength{\\fboxrule}{0.4pt} %%%% Back to default

""" %% (ext, title, block)
''' % (admon, admon_name, admon, admon, ', '.join(rgb), admon, latexfigdir, figname)
    return text

# Dropped this since it cannot work with verbatim computer code
#for _admon in ['warning', 'question', 'notice', 'summary']:
#    exec(_latex_admonition(_admon, _admon.upper()[0] + _admon[1:],
#                           _admon, _admon2rgb[_admon]))


def latex_subsubsection(m):
    title = m.group('subst').strip()
    if title[-1] in ('?', '!', '.', ':',):
        pass
    else:
        title += '.'
    return r'\paragraph{%s}' % title


def latex_inline_comment(m):
    name = m.group('name').strip()
    comment = m.group('comment').strip()

    """
    Can use soul package to support corrections as part of comments:
    http://texdoc.net/texmf-dist/doc/latex/soul/soul.pdf

    Typical commands:
    \newcommand{\replace}[2]{{\color{red}\text{\st{#1} #2}}}
    \newcommand{\remove}[1]{{\color{red}\st{#1}}}

    Could support:
    [del: ,]  expands to 'delete comma' in red
    [add: ;] expands to '; add semicolon' in red
    [add: text...] expands to added text in red
    [del: text...] expands to overstriked text in red
    [edit: text -> replacement] expands to overstriking (via soul) of text
    and adding replacement, both in red.

    Can have a doconce command for turning such correction comments
    into new, valid text (doing the corrections).
    """
    #import textwrap
    #caption_comment = textwrap.wrap(comment, width=60,
    #                                break_long_words=False)[0]
    caption_comment = ' '.join(comment.split()[:4])  # for toc for todonotes

    # Note: name is a name + space + number
    chars = {',': 'comma', ';': 'semicolon', '.': 'period'}
    if name[:4] == 'del ':
        for char in chars:
            if comment == char:
                return r' \textcolor{red}{ (\textbf{edit %s}: delete %s)}' % (name[4:], chars[char])
        return r'(\textbf{edit %s}:) \remove{%s}' % (name[4:], comment)
    elif name[:4] == 'add ':
        for char in chars:
            if comment == char:
                return r'\textcolor{red}{%s (\textbf{edit %s}: add %s)}' % (comment, name[4:], chars[char])
        return r' \textcolor{red}{ (\textbf{edit %s}:) %s}' % (name[4:], comment)
    else:
        # Ordinary name
        comment = ' '.join(comment.splitlines()) # '\s->\s' -> ' -> '
        if ' -> ' in comment:
            # Replacement
            if comment.count(' -> ') != 1:
                print '*** wrong syntax in inline comment:'
                print comment
                print '(more than two ->)'
                _abort()
            orig, new = comment.split(' -> ')
            return r'\textcolor{red}{(%s:)} \replace{%s}{%s}' % (name, orig, new)
        else:
            # Ordinary comment
            if '_' in comment:
                # todonotes are bad at handling verbatim code with comments...
                # inlinecomment is treated before verbatim
                verbatims = re.findall(r'`.+?`', comment)
                for verbatim in verbatims:
                    if '_' in verbatim:
                        verbatim_fixed = verbatim.replace('_', '\\_')
                        comment = comment.replace(verbatim, verbatim_fixed)

            if len(comment) <= 100:
                # Have some extra space inside the braces in the arguments to ensure
                # correct handling of \code{} commands
                return r'\shortinlinecomment{%s}{ %s }{ %s }' % \
                       (name, comment, caption_comment)
            else:
                return r'\longinlinecomment{%s}{ %s }{ %s }' % \
                       (name, comment, caption_comment)

def latex_quiz(quiz):
    part_of_exercise = quiz.get('embedding', 'None') in ['exercise',]
    choice_tp = option('quiz_choice_prefix=', 'letter+checkbox')
    text = '\n\\begin{doconcequiz}\n\\refstepcounter{doconcequizcounter}\n'
    text += '\\label{%s}\n\n' % quiz.get('label', 'quiz:%d' % quiz['no'])
    if 'heading' in quiz:
        text += '\n\\noindent\\textbf{\large %s}\n' % quiz['heading']
    if not part_of_exercise:
        text += '\\paragraph{%s}' % quiz.get('question prefix', 'Question:')
    else:
        # no heading, avoid indent
        text += '\n\\noindent'
    text += '\n' +  quiz['question']
    text += '\n\n\\vspace{2mm}\n\n'  # some space down to choices
    import string
    for i, choice in enumerate(quiz['choices']):
        if 'letter' in choice_tp:
            text += '\\textbf{%s}. ' % string.uppercase[i]
        elif 'number' in choice_tp:
            text += '\\textbf{%s}. ' % str(i+1)
        if option('without_answers') and option('without_solutions'):
            if 'box' in choice_tp:
                text += '$\Box$ '
            elif 'circle' in choice_tp:
                text += '$\bigcirc$ '

        text += '\n' + choice[1] + '\n\n'
    from common import envir_delimiter_lines
    if not option('without_answers'):
        begin, end = envir_delimiter_lines['ans']
        correct = [i for i, choice in enumerate(quiz['choices'])
                   if choice[0] == 'right']
        if 'letter' in choice_tp:
            correct = [string.uppercase[i] for i in correct]
        else:
            # keep number but add 1
            correct = [str(i+1) for i in correct]
        correct = ', '.join(correct)
        text += r"""
%% %s
\paragraph{Answer:} %s.
%% %s
""" % (begin, correct, end)
    if not option('without_solutions'):
        begin, end = envir_delimiter_lines['sol']
        solution = ''
        one_line = True  # True if no explanations
        for choice in quiz['choices']:
            if len(choice) > 2:
                one_line = False
                break

        for i, choice in enumerate(quiz['choices']):
            if 'letter' in choice_tp:
                solution += '\\textbf{%s}: ' % string.uppercase[i]
            else:
                solution += '\\textbf{%s}: ' % str(i+1)
            solution += choice[0].capitalize() + '. '
            if len(choice) == 3:
                solution += choice[2]
            if not one_line:
                solution += '\n\n'
        separator = '' if one_line else '\\\\\n\n'
        text += r"""
%% %s
\noindent {\bf Solution:}%s
%s
%% %s
""" % (begin, separator, solution, end)
    text += '\n\n\\vspace{3mm}\n\n\\end{doconcequiz}\n\n'  # some space

    '''
    # For the exam documentclass
    text += '\\begin{questions}\n'
    # Don't write Question: ... if inside an exercise section
    if not part_of_exercise:
        text += r'paragraph{Question:}'
    text += '\\question\n'
    text += '\n' + quiz['question'] + '\n'
    if choice_tp in ('letter', 'number'):
        text += '\\begin{choices}\n'
        latex_choice_tp = 'choices'
    elif choice_tp == 'checkbox':
        text += '\\begin{checkboxes}\n'
        latex_choice_tp = 'checkboxes'
    for i, choice in enumerate(quiz['choices']):
        # choice is ['wrong/right', choice] or ['wrong/right', choice, explanation]
        text += '\\choice\n' + choice[1] + '\n'
    text += '\\end{%s}\n' % latex_choice_tp
    text += '\\end{questions}\n'

    text += '% end quiz\n\n'
    """
    # Add answers
    if part_of_exercise and not option('without_answers'):
        for i, choice in enumerate(quiz['choices']):
    """
    '''
    #text = fix_latex_command_regex(text, 'replacement') # only for re.sub
    # but that won't work in other formats
    return text

def define(FILENAME_EXTENSION,
           BLANKLINE,
           INLINE_TAGS_SUBST,
           CODE,
           LIST,
           ARGLIST,
           TABLE,
           EXERCISE,
           FIGURE_EXT,
           CROSS_REFS,
           INDEX_BIB,
           TOC,
           ENVIRS,
           QUIZ,
           INTRO,
           OUTRO,
           filestr):
    # all arguments are dicts and accept in-place modifications (extensions)
    from common import INLINE_TAGS
    m = re.search(INLINE_TAGS['inlinecomment'], filestr, flags=re.DOTALL)
    has_inline_comments = True if m else False

    latex_code_style = option('latex_code_style=', None)
    if latex_code_style is None:
        FILENAME_EXTENSION['latex'] = '.p.tex'
    else:
        FILENAME_EXTENSION['latex'] = '.tex'

    BLANKLINE['latex'] = '\n'

    INLINE_TAGS_SUBST['latex'] = {
        # Note: re.sub "eats" backslashes: \t and \b will not survive to
        # latex if text goes through re.sub. Then we must write
        # \\b and \\t etc. See the fix_latex_command_regex function below
        # for the complete story.

        'math':          None,  # indicates no substitution, leave as is
        'math2':         r'\g<begin>$\g<latexmath>$\g<end>',
        'emphasize':     r'\g<begin>\emph{\g<subst>}\g<end>',
        'bold':          r'\g<begin>\\textbf{\g<subst>}\g<end>',  # (re.sub swallows a \)
        'verbatim':      r'\g<begin>\code{\g<subst>}\g<end>',
        # The following verbatim is better if fixed fontsize is ok, since
        # \code{\latexcommand{arg1}} style formatting does not work well
        # with ptex2tex (the regex will not include the proper second }
        #'verbatim':      r'\g<begin>{\footnotesize{10pt}{10pt}\Verb!\g<subst>!\g<end>',
        'colortext':     r'\\textcolor{\g<color>}{\g<text>}',
        #'linkURL':       r'\g<begin>\href{\g<url>}{\g<link>}\g<end>',
        'linkURL2':      r'\href{{\g<url>}}{\g<link>}',
        'linkURL3':      r'\href{{\g<url>}}{\g<link>}',
        'linkURL2v':     r'\href{{\g<url>}}{\\nolinkurl{\g<link>}}',
        'linkURL3v':     r'\href{{\g<url>}}{\\nolinkurl{\g<link>}}',
        'plainURL':      r'\href{{\g<url>}}{\\nolinkurl{\g<url>}}',  # cannot use \code inside \href, use \nolinkurl to handle _ and # etc. (implies verbatim font)
        'inlinecomment': latex_inline_comment,
        'chapter':       r'\chapter{\g<subst>}',
        'section':       r'\section{\g<subst>}',
        'subsection':    r'\subsection{\g<subst>}',
        #'subsubsection': '\n' + r'\subsubsection{\g<subst>}' + '\n',
        'subsubsection': latex_subsubsection,
        'paragraph':     r'\paragraph{\g<subst>}\n',
        #'abstract':      '\n\n' + r'\\begin{abstract}' + '\n' + r'\g<text>' + '\n' + r'\end{abstract}' + '\n\n' + r'\g<rest>', # not necessary with separate \n
        #'abstract':      r'\n\n\\begin{abstract}\n\g<text>\n\end{abstract}\n\n\g<rest>',
        'abstract':      latex_abstract,
        # recall that this is regex so latex commands must be treated carefully:
        #'title':         r'\\title{\g<subst>}' + '\n', # we don'e use maketitle
        'title':         latex_title,
        'author':        latex_author,
        #'date':          r'\\date{\g<subst>}' ' \n\\maketitle\n\n',
        'date':          latex_date,
        'figure':        latex_figure,
        'movie':         latex_movie,
        'comment':       '%% %s',
        'linebreak':     latex_linebreak,
        'footnote':      latex_footnotes,
        'non-breaking-space': None,
        'ampersand1':    r'\g<1> {\&} \g<2>',
        'ampersand2':    r' \g<1>{\&}\g<2>',
        # Use \Verb instead of \textbf since emoji name can contain underscore
        'emoji':         r'\g<1>(\Verb!\g<2>!)\g<3>',
        }

    ENVIRS['latex'] = {
        'quote':         latex_quote,
        'warning':       latex_warning,
        'question':      latex_question,
        'notice':        latex_notice,
        'summary':       latex_summary,
        'block':         latex_block,
        'box':           latex_box,
       }

    ending = '\n'
    ending = '\n\n\\noindent\n'
    LIST['latex'] = {
        'itemize':
        {'begin': r'\begin{itemize}' + '\n',
         'item': r'\item', 'end': r'\end{itemize}' + ending},

        'enumerate':
        {'begin': r'\begin{enumerate}' + '\n', 'item': r'\item',
         'end': r'\end{enumerate}' + ending},

        'description':
        {'begin': r'\begin{description}' + '\n', 'item': r'\item[%s]',
         'end': r'\end{description}' + ending},

        'separator': '\n',
        }

    CODE['latex'] = latex_code
    ARGLIST['latex'] = {
    #    'parameter': r'\textbf{argument}',
    #    'keyword': r'\textbf{keyword argument}',
    #    'return': r'\textbf{return value(s)}',
    #    'instance variable': r'\textbf{instance variable}',
    #    'class variable': r'\textbf{class variable}',
    #    'module variable': r'\textbf{module variable}',
        'parameter': r'argument',
        'keyword': r'keyword argument',
        'return': r'return value(s)',
        'instance variable': r'instance variable',
        'class variable': r'class variable',
        'module variable': r'module variable',
        }

    FIGURE_EXT['latex'] = ('.eps', '.ps')

    CROSS_REFS['latex'] = latex_ref_and_label

    TABLE['latex'] = latex_table
    EXERCISE['latex'] = latex_exercise
    INDEX_BIB['latex'] = latex_index_bib

    bib_page, idx_page = get_bib_index_pages()
    latex_style = option('latex_style=', 'std')
    title_layout = option('latex_title_layout=', 'doconce_heading')

    if latex_style not in ('std', 'Springer_T2', 'siamltex', 'siamltexmm',
                           'elsevier','Springer_lnup'):
        print '*** error: --latex_style=%s not registered' % latex_style
        _abort()

    toc_part = ''
    if title_layout != 'beamer':
        toc_part += r"""
\tableofcontents
"""
    if latex_style in  ('Springer_lncse', 'Springer_lnup'):
        toc_part += r"""
\contentsline{chapter}{\refname}{%(bib_page)s}{chapter.Bib}
\contentsline{chapter}{Index}{%(idx_page)s}{chapter.Index}
""" % vars()
    if has_inline_comments and not option('skip_inline_comments') \
        and option('latex_todonotes'):
        toc_part += r"""
\listoftodos[List of inline comments]
"""
    if title_layout != 'beamer':
        toc_part += r"""

\vspace{1cm} % after toc
"""
    if latex_style == 'Springer_T2':
        # Use special mainmatter from t2do.sty
        toc_part += r"""
\mymainmatter
"""

    if latex_style == 'Springer_lnup':
        toc_part += r"""
\mainmatter
"""

    TOC['latex'] = lambda s: toc_part
    QUIZ['latex'] = latex_quiz

    preamble = ''
    preamble_complete = False
    filename = option('latex_preamble=', None)
    if filename is not None:
        f = open(filename, "r")
        preamble = f.read()
        f.close()
        if r'\documentclass' in preamble:
            preamble_complete = True

    latex_papersize = option('latex_papersize=', 'std')
    latex_font = option('latex_font=', 'std')
    section_headings = option('latex_section_headings=', 'std')

    if latex_style.startswith('siam'):
        INLINE_TAGS_SUBST['latex']['keywords'] = r"""
\\begin{keywords}
\g<subst>
\end{keywords}
"""
    elif latex_style == 'elsevier':
        INLINE_TAGS_SUBST['latex']['keywords'] = lambda m: r"""
\begin{keyword}
%s
\end{keyword}
""" % ' \\sep '.join(re.split(r', *', m.group('subst').replace('.', '')))
    # (remove final . if present in keywords list)

    INTRO['latex'] = r"""%%
%% Automatically generated file from DocOnce source
%% (https://github.com/hplgit/doconce/)
%%
"""
    if latex_code_style is None:
        # We rely on the ptex2tex step
        INTRO['latex'] += r"""%%
% #ifdef PTEX2TEX_EXPLANATION
%%
%% The file follows the ptex2tex extended LaTeX format, see
%% ptex2tex: http://code.google.com/p/ptex2tex/
%%
%% Run
%%      ptex2tex myfile
%% or
%%      doconce ptex2tex myfile
%%
%% to turn myfile.p.tex into an ordinary LaTeX file myfile.tex.
%% (The ptex2tex program: http://code.google.com/p/ptex2tex)
%% Many preprocess options can be added to ptex2tex or doconce ptex2tex
%%
%%      ptex2tex -DMINTED myfile
%%      doconce ptex2tex myfile envir=minted
%%
%% ptex2tex will typeset code environments according to a global or local
%% .ptex2tex.cfg configure file. doconce ptex2tex will typeset code
%% according to options on the command line (just type doconce ptex2tex to
%% see examples). If doconce ptex2tex has envir=minted, it enables the
%% minted style without needing -DMINTED.
% #endif
"""

    if latex_style == 'Springer_collection':
        INTRO['latex'] += r"""
% #undef PREAMBLE
"""
    else:
        INTRO['latex'] += r"""
% #define PREAMBLE
"""

    INTRO['latex'] += r"""
% #ifdef PREAMBLE
%-------------------- begin preamble ----------------------
"""

    from misc import copy_latex_packages

    side_tp = 'oneside' if option('device=') == 'paper' else 'twoside'
    m = re.search(chapter_pattern, filestr, flags=re.MULTILINE)
    # (use A-Z etc to avoid sphinx table headings to indicate chapters...
    if m:  # We have chapters, use book style
        chapters = True
    else:
        chapters = False

    if latex_style == 'std':
        book = False
        if chapters and not option('sections_down'):
            book = True
        elif '======= ' in filestr and option('sections_up'):
            # Sections become chapters
            book = True
        if book:
            INTRO['latex'] += r"""
\documentclass[%%
%(side_tp)s,                 %% oneside: electronic viewing, twoside: printing
final,                   %% or draft (marks overfull hboxes, figures with paths)
chapterprefix=true,      %% "Chapter" word at beginning of each chapter
open=right               %% start new chapters on odd-numbered pages
10pt]{book}
""" % vars()
        else:  # Only sections, use article style
            INTRO['latex'] += r"""
\documentclass[%%
%(side_tp)s,                 %% oneside: electronic viewing, twoside: printing
final,                   %% or draft (marks overfull hboxes, figures with paths)
10pt]{article}
""" % vars()

    elif latex_style == 'Springer_lncse':
        INTRO['latex'] += r"""
% Style: Lecture Notes in Computational Science and Engineering (Springer)
\documentclass[envcountsect,open=right]{lncse}
\pagestyle{headings}
"""
    elif latex_style == 'Springer_lnup':
        copy_latex_packages(['svmonodo.cls', 't2do.sty'])
        INTRO['latex'] += r"""
% Style: Lecture Notes in Undergraduate Physics 2 (Springer)
\documentclass[graybox,envcountchap,sectrefs]{svmonodo}
%\pagestyle{headings}
\usepackage{mathptmx}
\usepackage{helvet}
\usepackage{courier}
\usepackage{type1cm}
\usepackage{framed}
\usepackage{booktabs}
\usepackage{subeqnarray}
\usepackage[bottom]{footmisc}
\usepackage{cite}
\usepackage{multicol}
"""
    elif latex_style == 'Springer_T2':
        copy_latex_packages(['svmonodo.cls', 't2do.sty'])
        INTRO['latex'] += r"""
% Style: T2 (Springer)
% Use svmono.cls with doconce modifications for bibliography
\documentclass[graybox,sectrefs,envcountresetchap,open=right]{svmonodo}

% Use t2.sty with doconce modifications
\usepackage{t2do}
\special{papersize=193mm,260mm}
"""
    elif latex_style == 'Springer_llncs':
        INTRO['latex'] += r"""
% Style: Lecture Notes in Computer Science (Springer)
\documentclass[oribib]{llncs}
"""
    elif latex_style == 'Koma_Script':
        INTRO['latex'] += r"""
% Style: Koma-Script
\documentclass[10pt]{scrartcl}
"""
    elif latex_style == 'siamltex':
        INTRO['latex'] += r"""
% Style: SIAM LaTeX2e
\documentclass[final,leqno]{siamltex}
"""
    elif latex_style == 'siamltexmm':
        INTRO['latex'] += r"""
% Style: SIAM LaTeX2e multimedia
\documentclass[leqno]{siamltexmm}
"""
    elif latex_style == 'elsevier':
        INTRO['latex'] += r"""
% Style: Elsvier LaTeX style
\documentclass{elsarticle}
"""
        journal_name = option('latex_elsevier_journal=', 'none')
        if journal_name != 'none':
            INTRO['latex'] += r"""
%\journal{%s}
""" % journal_name
        else:
            INTRO['latex'] += r"""
% Drop "Submitted to ..." line at the bottom of the first page
\makeatletter
\def\ps@pprintTitle{%
  \let\@oddhead\@empty
  \let\@evenhead\@empty
  \def\@oddfoot{\reset@font\hfil\thepage\hfil}
  \let\@evenfoot\@oddfoot
}
\makeatother
"""
    INTRO['latex'] += r"""
\listfiles               % print all files needed to compile this document
"""
    if latex_papersize == 'a4':
        INTRO['latex'] += r"""
\usepackage[a4paper]{geometry}
"""
    elif latex_papersize == 'a6':
        INTRO['latex'] += r"""
% a6paper is suitable for mobile devices
\usepackage[%
  a6paper,
  text={90mm,130mm},
  inner={5mm},           % inner margin (two sided documents)
  top=5mm,
  headsep=4mm
  ]{geometry}
"""

    if latex_style != 'Springer_lnup':
        INTRO['latex'] += r"""
\usepackage{relsize,epsfig,makeidx,color,setspace,amsmath,amsfonts}
\usepackage[table]{xcolor}
\usepackage{bm,microtype}
"""
    else:
        INTRO['latex'] += r"""
\usepackage{epsfig,makeidx,color,setspace,amsmath,amsfonts}
\usepackage[table]{xcolor}
\usepackage{bm}
"""

    if 'FIGURE' in filestr:
        INTRO['latex'] += r"""
\usepackage{graphicx}
"""

    # Inline comments with corrections?
    if '[del:' in filestr or '[add:' in filestr or '[,]' in filestr or \
       re.search(r'''\[(?P<name>[ A-Za-z0-9_'+-]+?):(?P<space>\s+)(?P<correction>.*? -> .*?)\]''', filestr, flags=re.DOTALL|re.MULTILINE):
        INTRO['latex'] += r"""
% Tools for marking corrections
\usepackage{soul}
\newcommand{\replace}[2]{{\color{red}\text{\st{#1} #2}}}
\newcommand{\remove}[1]{{\color{red}\st{#1}}}
"""

    # fancybox must be loaded prior to fancyvrb and minted
    # (which appears instead of or in addition to ptex2tex)
    # fancybox is just used for Sbox in latex_box (!bbox)
    if '!bbox' in filestr:
        INTRO['latex'] += r"""
\usepackage{fancybox}  % make sure fancybox is loaded before fancyvrb
%\setlength{\fboxsep}{8pt}  % may clash with need in pre/cod envirs
"""
    xelatex = option('xelatex')

    # Add packages for movies
    if re.search(r'^MOVIE:\s*\[', filestr, flags=re.MULTILINE):
        movie = option('latex_movie=', 'href')
        package = ''
        if movie == 'media9':
            if xelatex:
                package = r'\usepackage[xetex]{media9}'
            else:
                package = r'\usepackage{media9}'
        if movie == 'movie15':
            package = r'\usepackage{movie15}'
        elif movie == 'multimedia':
            package = r'\usepackage{multimedia}'
        INTRO['latex'] += r"""
%% Movies are handled by the %(movie)s package
\newenvironment{doconce:movie}{}{}
\newcounter{doconce:movie:counter}
%(package)s
""" % vars()
        movies = re.findall(r'^MOVIE: \[(.+?)\]', filestr, flags=re.MULTILINE)
        animated_files = False
        non_flv_mp4_files = False  # need for old movie15 instead of media9?
        for filename in movies:
            if '*' in filename or '->' in filename:
                animated_files = True
            if '.mp4' in filename.lower() or '.flv' in filename.lower():
                pass # ok, media9 can be used
            else:
                non_flv_mp4_files = True
        if non_flv_mp4_files and movie == 'media9':
            INTRO['latex'] += r'\usepackage{movie15}' + '\n'
        if animated_files:
            if xelatex:
                INTRO['latex'] += r'\usepackage[xetex]{animate}'
            else:
                INTRO['latex'] += r'\usepackage{animate}'
            if 'graphicx' not in INTRO['latex']:
                INTRO['latex'] += '\n' + r'\usepackage{graphicx}'

            INTRO['latex'] += '\n\n'

    m = re.search('^(!bc|@@@CODE|@@@CMD)', filestr, flags=re.MULTILINE)
    if m:
        if latex_code_style is None:
            # Rely on ptex2tex step
            INTRO['latex'] += r"""
\usepackage{ptex2tex}
% #ifdef MINTED
\usepackage{minted}
\usemintedstyle{default}
% #endif
"""
        else:
            # Rely on generating all code block environments directly
            INTRO['latex'] += r"""
% Packages for typesetting blocks of computer code
\usepackage{fancyvrb,framed,moreverb}

% Define colors
\definecolor{orange}{cmyk}{0,0.4,0.8,0.2}
\definecolor{darkorange}{rgb}{.71,0.21,0.01}
\definecolor{darkgreen}{rgb}{.12,.54,.11}
\definecolor{myteal}{rgb}{.26, .44, .56}
\definecolor{gray}{gray}{0.45}
\definecolor{mediumgray}{gray}{.8}
\definecolor{lightgray}{gray}{.95}

\colorlet{comment_green}{green!50!black}
\colorlet{string_red}{red!60!black}
\colorlet{keyword_pink}{magenta!70!black}
\colorlet{indendifier_green}{green!70!white}

% New ansi colors
\definecolor{brown}{rgb}{0.54,0.27,0.07}
\definecolor{purple}{rgb}{0.5,0.0,0.5}
\definecolor{darkgray}{gray}{0.25}
\definecolor{darkblue}{rgb}{0,0.08,0.45}
\definecolor{lightred}{rgb}{1.0,0.39,0.28}
\definecolor{lightgreen}{rgb}{0.48,0.99,0.0}
\definecolor{lightblue}{rgb}{0.53,0.81,0.92}
\definecolor{lightpurple}{rgb}{0.87,0.63,0.87}
\definecolor{lightcyan}{rgb}{0.5,1.0,0.83}

% Backgrounds for code
\definecolor{cbg_gray}{rgb}{.95, .95, .95}
\definecolor{bar_gray}{rgb}{.92, .92, .92}

\definecolor{cbg_yellowgray}{rgb}{.95, .95, .85}
\definecolor{bar_yellowgray}{rgb}{.95, .95, .65}

\colorlet{cbg_yellow2}{yellow!10}
\colorlet{bar_yellow2}{yellow!20}

\definecolor{cbg_yellow1}{rgb}{.98, .98, 0.8}
\definecolor{bar_yellow1}{rgb}{.98, .98, 0.4}

\definecolor{cbg_red1}{rgb}{1, 0.85, 0.85}
\definecolor{bar_red1}{rgb}{1, 0.75, 0.85}

\definecolor{cbg_blue1}{rgb}{0.87843, 0.95686, 1.0}
\definecolor{bar_blue1}{rgb}{0.7,     0.95686, 1}
"""
            # Is a cod/pro background requested?
            # See also tcolorbox as an alternative for background
            # colors: http://tex.stackexchange.com/questions/173850/problem-in-adding-a-background-color-in-a-minted-environment
            pattern = '-(yellow|red|blue|gray)'
            if re.search(pattern, latex_code_style):
                INTRO['latex'] += r"""
% Background for code blocks (parameter is color name)
"""
                if not '!bbox' in filestr:
                    if 'numbers' in str(latex_code_style) or \
                       'linenos' in str(latex_code_style):
                        fboxsep = '2mm'
                    else:
                        fboxsep = '-1.5mm'
                    # No use of !bbox and hence no use of fboxsep
                    # for those boxes, and we can redefine fboxsep here
                    INTRO['latex'] += r"""\setlength{\fboxsep}{%s}  %% adjust cod/pro background box
\newenvironment{cod}[1]{
   \def\FrameCommand{\colorbox{#1}}
   \MakeFramed{\FrameRestore}}
   {\endMakeFramed}

%% Background for complete program blocks (parameter 1 is color name
%% for background, parameter 2 is color for left bar)
\newenvironment{pro}[2]{
   \def\FrameCommand{\color{#2}\vrule width 1mm\normalcolor\colorbox{#1}}
   \MakeFramed{\FrameRestore}}
   {\endMakeFramed}
""" % fboxsep
                else:
                    INTRO['latex'] += r"""%\setlength{\fboxsep}{-1.5mm}  % do not change since !bbox needs it positive!
\newenvironment{cod}[1]{
   \def\FrameCommand{\colorbox{#1}}
   \MakeFramed{\advance\hsize-\width \FrameRestore}}
 {\unskip\medskip\endMakeFramed}

% Background for complete program blocks (parameter 1 is color name
% for background, parameter 2 is color for left bar)
\newenvironment{pro}[2]{
   \def\FrameCommand{\color{#2}\vrule width 1mm\normalcolor\colorbox{#1}}
   \MakeFramed{\advance\hsize-\width \FrameRestore}}
 {\unskip\medskip\endMakeFramed}
"""
                # \unskip removes the skip, \medskip adds some, such that
                # the skip below is smaller than the one above
                # Use .ptex2tex.cfg to get the background box very tight
#                INTRO['latex'] += r"""
#% Alternative (\vskip with positive skip adds colored space)
#%\newenvironment{cod}[1]{%
#%   \def\FrameCommand{\colorbox{#1}}%
#%   \MakeFramed{\FrameRestore}\vskip 0mm}%
#% {\vskip 0mm\endMakeFramed}
#"""
            if 'lst' in latex_code_style:
                INTRO['latex'] += r'\usepackage{listingsutf8}' + '\n'
                INTRO['latex'] += latex_code_lstlisting(latex_code_style)
            if 'pyg' in latex_code_style:
                INTRO['latex'] += r'\usepackage{minted}' + '\n'
                pygm_style = option('minted_latex_style=', default='default')
                legal_pygm_styles = 'monokai manni rrt perldoc borland colorful default murphy vs trac tango fruity autumn bw emacs vim pastie friendly native'.split()
                if pygm_style not in legal_pygm_styles:
                    print '*** error: wrong minted style "%s"' % pygm_style
                    print '    must be among\n%s' % str(legal_pygm_styles)[1:-1]
                    _abort()

                INTRO['latex'] += r'\usemintedstyle{%s}' % pygm_style + '\n'


    m = re.search(INLINE_TAGS['verbatim'], filestr, flags=re.MULTILINE)
    if m and 'usepackage{fancyvrb' not in INTRO['latex']:
        INTRO['latex'] += '\\usepackage{fancyvrb}\n'
        # Recall to insert \VerbatimFootnotes later, after hyperref, if
        # we have footnotes with verbatim

    if xelatex:
        INTRO['latex'] += r"""
% xelatex settings
\usepackage{fontspec}
\usepackage{xunicode}
\defaultfontfeatures{Mapping=tex-text} % To support LaTeX quoting style
\defaultfontfeatures{Ligatures=TeX}
\setromanfont{Kinnari}
% Examples of font types (Ubuntu): Gentium Book Basic (Palatino-like),
% Liberation Sans (Helvetica-like), Norasi, Purisa (handwriting), UnDoum
"""
    elif latex_style == 'Springer_lnup':
        INTRO['latex'] += r"""
\usepackage[T1]{fontenc}
%\usepackage[latin1]{inputenc}
\usepackage{ucs}
%\usepackage[utf8x]{inputenc}
"""
    else:
        if option('latex_encoding=', 'utf8') == 'utf8':
            INTRO['latex'] += r"""
\usepackage[T1]{fontenc}
%\usepackage[latin1]{inputenc}
\usepackage{ucs}
\usepackage[utf8x]{inputenc}
"""
        else:  # latin1
            INTRO['latex'] += r"""
\usepackage[T1]{fontenc}
\usepackage[latin1]{inputenc}
\usepackage{ucs}
%\usepackage[utf8x]{inputenc}
"""
    if latex_font == 'helvetica':
        INTRO['latex'] += r"""
% Set helvetica as the default font family:
\RequirePackage{helvet}
\renewcommand\familydefault{phv}
"""
    elif latex_font == 'palatino':
        INTRO['latex'] += r"""
% Set palatino as the default font family:
\usepackage[sc]{mathpazo}    % Palatino fonts
\linespread{1.05}            % Palatino needs extra line spread to look nice
"""
    if latex_style != 'Springer_lnup':
        INTRO['latex'] += r"""
\usepackage{lmodern}         % Latin Modern fonts derived from Computer Modern
"""

    if '!bquiz' in filestr:
        INTRO['latex'] += r"""
\newenvironment{doconcequiz}{}{}
\newcounter{doconcequizcounter}
"""
        quiz_numbering = option('latex_exercise_numbering=', 'absolute')
        if chapters and quiz_numbering == 'chapter':
            INTRO['latex'] += r"""
% Let quizzes be numbered per chapter:
\usepackage{chngcntr}
\counterwithin{doconcequizcounter}{chapter}
"""

    '''
    # Package for quiz
    # http://ctan.uib.no/macros/latex/contrib/exam/examdoc.pdf
    # Requires documentclass{exam} and cannot be used in combination
    # with other documentclass
    if '!bquiz' in filestr:
        INTRO['latex'] += r"""
\usepackage{exam}            % for quiz typesetting
\newcommand{\questionlabel}{}
\CorrectChoiceEmphasis{\itshape}
\checkboxchar{$\Box$}\checkedchar{$\blacksquare$}
"""
    '''

    # Make sure hyperlinks are black (as the text) for printout
    # and otherwise set to the dark blue linkcolor
    linkcolor = 'linkcolor'
    if option('device=') == 'paper':
        linkcolor = 'black'
    elif section_headings in ('blue', 'strongblue'):
        linkcolor = 'seccolor'
    INTRO['latex'] += r"""
%% Hyperlinks in PDF:
\definecolor{linkcolor}{rgb}{0,0,0.4}
\usepackage{hyperref}
\hypersetup{
    breaklinks=true,
    colorlinks=true,
    linkcolor=%(linkcolor)s,
    urlcolor=%(linkcolor)s,
    citecolor=black,
    filecolor=black,
    %%filecolor=blue,
    pdfmenubar=true,
    pdftoolbar=true,
    bookmarksdepth=3   %% Uncomment (and tweak) for PDF bookmarks with more levels than the TOC
    }
%%\hyperbaseurl{}   %% hyperlinks are relative to this root

\setcounter{tocdepth}{2}  %% number chapter, section, subsection
""" % vars()

    # Footnotes with verbatim?
    if 'fancyvrb' in INTRO['latex']:
        has_footnotes_with_verbatim = False
        pattern = r'\[\^.+\]:(?P<text>.+?)(?=(\n\n|\[\^|\Z))'
        footnotes = [groups[0] for groups in re.findall(pattern, filestr, flags=re.MULTILINE)]
        for footnote in footnotes:
            m = re.search(INLINE_TAGS['verbatim'], filestr, flags=re.MULTILINE)
            if m:
                has_footnotes_with_verbatim = True
                break
        if has_footnotes_with_verbatim:
            if 'usepackage{t2do}' in INTRO['latex']:
                print '*** warning: footnotes with verbatim has strange typesetting with svmonodo/t2do styles'
                INTRO['latex'] += '\n% Must use \\VerbatimFootnotes since there are footnotes with inline\n% verbatim text, but \\VerbatimFootnotes interfers\n%with svmonodo/t2do styles so that the footmisc package settings\n% do not work and the typesetting looks strange...'
            INTRO['latex'] += '\n%\\VerbatimFootnotes must come after hyperref and footmisc packages\n\\VerbatimFootnotes\n'

    if 'FIGURE:' in filestr:
        if latex_style != 'Springer_lnup':
            INTRO['latex'] += r"""
% Tricks for having figures close to where they are defined:
% 1. define less restrictive rules for where to put figures
\setcounter{topnumber}{2}
\setcounter{bottomnumber}{2}
\setcounter{totalnumber}{4}
\renewcommand{\topfraction}{0.85}
\renewcommand{\bottomfraction}{0.85}
\renewcommand{\textfraction}{0.15}
\renewcommand{\floatpagefraction}{0.7}
% 2. ensure all figures are flushed before next section
\usepackage[section]{placeins}
% 3. enable begin{figure}[H] (often leads to ugly pagebreaks)
%\usepackage{float}\restylefloat{figure}
"""
    if has_inline_comments:
        if option('latex_todonotes'):
            INTRO['latex'] += r"""
% enable inline (doconce) comments to be typeset with the todonotes package
\usepackage{ifthen,xkeyval,tikz,calc,graphicx}"""
            if option('skip_inline_comments'):
                INTRO['latex'] += r"""
\usepackage[shadow,disable]{todonotes}"""
            else:
                INTRO['latex'] += r"""
\usepackage[shadow]{todonotes}"""
            INTRO['latex'] += r"""
\newcommand{\shortinlinecomment}[3]{%
\todo[size=\normalsize,fancyline,color=orange!40,caption={#3}]{%
 \begin{spacing}{0.75}{\bf #1}: #2\end{spacing}}}
\newcommand{\longinlinecomment}[3]{%
\todo[inline,color=orange!40,caption={#3}]{{\bf #1}: #2}}
"""
        else:
            INTRO['latex'] += r"""
% newcommands for typesetting inline (doconce) comments"""
            if option('skip_inline_comments'):
                INTRO['latex'] += r"""
\newcommand{\shortinlinecomment}[3]{}
\newcommand{\longinlinecomment}[3]{}"""
            else:
                INTRO['latex'] += r"""
\newcommand{\shortinlinecomment}[3]{{\color{red}{\bf #1}: #2}}
\newcommand{\longinlinecomment}[3]{{\color{red}{\bf #1}: #2}}"""
            INTRO['latex'] += r"""
"""
    if option('latex_line_numbers'):
        INTRO['latex'] += r"""
\usepackage[mathlines]{lineno}  % show line numbers
\linenumbers
"""
    if option('latex_labels_in_margin'):
        INTRO['latex'] += r"""
% Display labels for sections, equations, and citations in the margin
\usepackage{showlabels}
\showlabels{cite}
"""
    if option('latex_double_spacing'):
        INTRO['latex'] += r"""
\onehalfspacing    % from setspace package
%\doublespacing
"""

    if option('latex_fancy_header'):
        INTRO['latex'] += r"""
% --- fancyhdr package for fancy headers ---
\usepackage{fancyhdr}
\fancyhf{}"""
        if chapters:
            INTRO['latex'] += r"""
% section name to the left (L) and page number to the right (R)
% on even (E) pages,
% chapter name to the right (R) and page number to the right (L)
% on odd (O) pages
\fancyhead[LE]{\rightmark} %section
\fancyhead[RE]{\thepage}
\fancyhead[RO]{\leftmark} % chapter
\fancyhead[LO]{\thepage}"""
        else:
            INTRO['latex'] += r"""
% section name to the left (L) and page number to the right (R)
% on even (E) pages, the other way around on odd pages
\fancyhead[LE,RO]{\rightmark} %section
\fancyhead[RE,LO]{\thepage}"""
        INTRO['latex'] += r"""
\pagestyle{fancy}

"""
        # Not necessary:
        #filestr = re.sub('^(=====.+?=====\s+)', '% #ifdef FANCY_HEADER\n\\pagestyle{fancy}\n% #endif\n\n\g<1>', filestr, count=1, flags=re.MULTILINE)
        # Can insert above if section_headings == "blue" and have a
        # blue typesetting of the section if that is not done automatically...


    # Admonitions
    if re.search(r'^!b(%s)' % '|'.join(admons), filestr, flags=re.MULTILINE):
        # Found one !b... command for an admonition
        latex_admon = option('latex_admon=', 'mdfbox')
        latex_admon_color = option('latex_admon_color=', None)

        admon_styles = 'colors1', 'colors2', 'mdfbox', 'graybox2', 'grayicon', 'yellowicon',
        admon_color = {style: {} for style in admon_styles}

        if latex_admon_color is None:
            # default colors
            # colors1, colors2 color
            light_blue = (0.87843, 0.95686, 1.0)
            pink = (1.0, 0.8235294, 0.8235294)
            # colors1, colors2, yellowicon color
            yellow1 = (0.988235, 0.964706, 0.862745)
            yellow1b = (0.97, 0.88, 0.62)  # alt, not used
            # mdfbox color
            gray1 = "gray!5"
            # graybox2 color
            gray2 = (0.94, 0.94, 0.94)
            # grayicon color
            gray3 = (0.91, 0.91, 0.91)   # lighter gray
            gray3l = (0.97, 0.97, 0.97)  # even lighter gray, not used

            for admon_style in ('colors1', 'colors2'):
                admon_color[admon_style] = dict(
                    warning=pink,
                    question=yellow1,
                    notice=yellow1,
                    summary=yellow1,
                    #block=_gray2,
                    block=yellow1,
                    )
            for admon in admons:
                admon_color['mdfbox'][admon] = gray1
                admon_color['graybox2'][admon] = gray2
                admon_color['grayicon'][admon] = gray3
                admon_color['yellowicon'][admon] = yellow1
        else:
            # use latex_admon_color for everything
            try:
                # RGB input?
                latex_admon_color = tuple(eval(latex_admon_color))
            except (NameError, SyntaxError) as e:
                # Color name input
                pass

            for style in admon_styles:
                for admon in admons:
                    admon_color[style][admon] = latex_admon_color

        if latex_admon in ('colors1',):
            packages = r'\usepackage{framed}'
        elif latex_admon in ('colors2', 'grayicon', 'yellowicon'):
            packages = r'\usepackage{framed,wrapfig}'
        elif latex_admon in ('graybox2',):
            packages = r"""\usepackage{wrapfig,calc}
\usepackage[framemethod=TikZ]{mdframed}  % use latest version: https://github.com/marcodaniel/mdframed"""
        else: # mdfbox
            packages = r'\usepackage[framemethod=TikZ]{mdframed}'
        INTRO['latex'] += '\n' + packages + '\n\n% --- begin definitions of admonition environments ---\n'

        for style in admon_styles:
            for admon in admons:
                color = admon_color[style][admon]
                if isinstance(color, (tuple,list)):
                    rgb = ','.join([str(cl) for cl in color])
                    admon_color[style][admon] = r'\definecolor{%(latex_admon)s_%(admon)s_background}{rgb}{%(rgb)s}' % vars()
                else:
                    admon_color[style][admon] = r'\colorlet{%(latex_admon)s_%(admon)s_background}{%(color)s}' % vars()

        if latex_admon == 'graybox2':
            # First define environments independent of admon type

            INTRO['latex'] += r"""
% Admonition style "graybox2" is a gray or colored box with a square
% frame, except for the summary admon which has horizontal rules only
% Note: this admonition type cannot handle verbatim text!
"""
            INTRO['latex'] += admon_color[latex_admon]['warning'] + '\n'
            if latex_papersize == 'a4':
                INTRO['latex'] += r"""
\newdimen\barheight
\def\barthickness{0.5pt}

%% small box to the right for A4 paper
\newcommand{\grayboxhrules}[1]{\begin{wrapfigure}{r}{0.5\textwidth}
\vspace*{-\baselineskip}\colorbox{%(latex_admon)s_warning_background}{\rule{3pt}{0pt}
\begin{minipage}{0.5\textwidth-6pt-\columnsep}
\hspace*{3mm}
\setbox2=\hbox{\parbox[t]{55mm}{
#1 \rule[-8pt]{0pt}{10pt}}}%%
\barheight=\ht2 \advance\barheight by \dp2
\parbox[t]{3mm}{\rule[0pt]{0mm}{22pt}%%\hspace*{-2pt}%%
\hspace*{-1mm}\rule[-\barheight+16pt]{\barthickness}{\barheight-8pt}%%}
}\box2\end{minipage}\rule{3pt}{0pt}}\vspace*{-\baselineskip}
\end{wrapfigure}}
""" % vars()
            else:
                INTRO['latex'] += r"""
%% colored box of 80%% width
\newcommand{\grayboxhrules}[1]{\begin{center}
\colorbox{%(latex_admon)s_warning_background}{\rule{6pt}{0pt}
\begin{minipage}{0.8\linewidth}
\parbox[t]{0mm}{\rule[0pt]{0mm}{0.5\baselineskip}}\hrule
\vspace*{0.5\baselineskip}\noindent #1
\parbox[t]{0mm}{\rule[-0.5\baselineskip]{0mm}%%
{\baselineskip}}\hrule\vspace*{0.5\baselineskip}\end{minipage}
\rule{6pt}{0pt}}\end{center}}
""" % vars()
            INTRO['latex'] += r"""
%% Fallback for verbatim content in \grayboxhrules
\newmdenv[
  backgroundcolor=%(latex_admon)s_warning_background,
  skipabove=15pt,
  skipbelow=15pt,
  leftmargin=23,
  rightmargin=23,
  needspace=0pt,
]{graybox2mdframed}

\newenvironment{graybox2admon}[1][]{
\begin{graybox2mdframed}[frametitle=#1]
}
{
\end{graybox2mdframed}
}
""" % vars()

        elif latex_admon == 'paragraph':
            pass  # we use plain \paragraph for this
        #            INTRO['latex'] += r"""
        #% Admonition style "paragraph" is just a plain paragraph
        #\newenvironment{paragraphadmon}[1][]{\paragraph{#1}}{}
        #"""

        # Define environments depending on the admon type
        for admon in admons:
            Admon = admon.upper()[0] + admon[1:]

            # Figure files are copied when necessary

            graphics_colors1 = r'\includegraphics[height=0.3in]{latex_figs/%s}\ \ \ ' % get_admon_figname('colors1', admon)
            graphics_colors2 = r"""\begin{wrapfigure}{l}{0.07\textwidth}
\vspace{-13pt}
\includegraphics[width=0.07\textwidth]{latex_figs/%s}
\end{wrapfigure}""" % get_admon_figname('colors2', admon)

            graphics_grayicon = r"""\begin{wrapfigure}{l}{0.07\textwidth}
\vspace{-13pt}
\includegraphics[width=0.07\textwidth]{latex_figs/%s}
\end{wrapfigure}"""% get_admon_figname('grayicon', admon)

            graphics_yellowicon = r"""\begin{wrapfigure}{l}{0.07\textwidth}
\vspace{-13pt}
\includegraphics[width=0.07\textwidth]{latex_figs/%s}
\end{wrapfigure}""" % get_admon_figname('yellowicon', admon)

            if admon == 'block':
                # No figures for block admon
                graphics_colors1 = ''
                graphics_colors2 = ''
                graphics_grayicon = ''
                graphics_yellowicon = ''

            _admon_style_color = admon_color.get(latex_admon, None)
            if _admon_style_color is not None:
                define_bgcolor = _admon_style_color[admon]

            if latex_admon == 'colors1':
                INTRO['latex'] += r"""
%% Admonition style "colors1" has its style taken from the NumPy User Guide
%% "%(admon)s" admon
%(define_bgcolor)s
%% \fboxsep sets the space between the text and the box
\newenvironment{%(admon)sshaded}
{\def\FrameCommand{\fboxsep=3mm\colorbox{%(latex_admon)s_%(admon)s_background}}
 \MakeFramed {\advance\hsize-\width \FrameRestore}}{\endMakeFramed}

\newenvironment{%(admon)s_colors1admon}[1][%(Admon)s]{
\begin{%(admon)sshaded}
\noindent
%(graphics_colors1)s  \textbf{#1}\\ \par
\vspace{-3mm}\nobreak\noindent\ignorespaces
}
{
\end{%(admon)sshaded}
}
""" % vars()
            elif latex_admon == 'colors2':
                INTRO['latex'] += r"""
%% Admonition style "colors2", admon "%(admon)s"
%(define_bgcolor)s
%% \fboxsep sets the space between the text and the box
\newenvironment{%(admon)sshaded}
{\def\FrameCommand{\fboxsep=3mm\colorbox{%(latex_admon)s_%(admon)s_background}}
 \MakeFramed {\advance\hsize-\width \FrameRestore}}{\endMakeFramed}

\newenvironment{%(admon)s_colors2admon}[1][%(Admon)s]{
\begin{%(admon)sshaded}
\noindent
%(graphics_colors2)s \textbf{#1}\par
\nobreak\noindent\ignorespaces
}
{
\end{%(admon)sshaded}
}
""" % vars()
            elif latex_admon == 'grayicon':
                INTRO['latex'] += r"""
%% Admonition style "grayicon" has colored background, no frame, and an icon
%% Admon "%(admon)s"
%(define_bgcolor)s
%% \fboxsep sets the space between the text and the box
\newenvironment{%(admon)sshaded}
{\def\FrameCommand{\fboxsep=3mm\colorbox{%(latex_admon)s_%(admon)s_background}}
 \MakeFramed {\advance\hsize-\width \FrameRestore}}{\endMakeFramed}

\newenvironment{%(admon)s_%(latex_admon)sadmon}[1][%(Admon)s]{
\begin{%(admon)sshaded}
\noindent
%(graphics_grayicon)s \textbf{#1}\par
\nobreak\noindent\ignorespaces
}
{
\end{%(admon)sshaded}
}
""" % vars()
            elif latex_admon == 'yellowicon':
                INTRO['latex'] += r"""
%% Admonition style "yellowicon" has colored background, yellow icons, and no farme
%% Admon "%(admon)s"
%(define_bgcolor)s
%% \fboxsep sets the space between the text and the box
\newenvironment{%(admon)sshaded}
{\def\FrameCommand{\fboxsep=3mm\colorbox{%(latex_admon)s_%(admon)s_background}}
 \MakeFramed {\advance\hsize-\width \FrameRestore}}{\endMakeFramed}

\newenvironment{%(admon)s_%(latex_admon)sadmon}[1][%(Admon)s]{
\begin{%(admon)sshaded}
\noindent
%(graphics_yellowicon)s \textbf{#1}\par
\nobreak\noindent\ignorespaces
}
{
\end{%(admon)sshaded}
}
""" % vars()


            elif latex_admon == 'mdfbox':
                # mdfbox, the most flexible/custom admon construction
                INTRO['latex'] += r"""
%% Admonition style "mdfbox" is an oval colored box based on mdframed
%% "%(admon)s" admon
%(define_bgcolor)s
\newmdenv[
  skipabove=15pt,
  skipbelow=15pt,
  outerlinewidth=0,
  backgroundcolor=%(latex_admon)s_%(admon)s_background,
  linecolor=black,
  linewidth=2pt,       %% frame thickness
  frametitlebackgroundcolor=%(latex_admon)s_%(admon)s_background,
  frametitlerule=true,
  frametitlefont=\normalfont\bfseries,
  shadow=false,        %% frame shadow?
  shadowsize=11pt,
  leftmargin=0,
  rightmargin=0,
  roundcorner=5,
  needspace=0pt,
]{%(admon)s_%(latex_admon)smdframed}

\newenvironment{%(admon)s_%(latex_admon)sadmon}[1][]{
\begin{%(admon)s_%(latex_admon)smdframed}[frametitle=#1]
}
{
\end{%(admon)s_%(latex_admon)smdframed}
}
""" % vars()
        INTRO['latex'] += r"""
% --- end of definitions of admonition environments ---
"""

    colored_table_rows = option('latex_colored_table_rows=', 'no')


    INTRO['latex'] += r"""
% prevent orhpans and widows
\clubpenalty = 10000
\widowpenalty = 10000
"""
    if section_headings != 'std':
        INTRO['latex'] += r"""
% http://www.ctex.org/documents/packages/layout/titlesec.pdf
\usepackage{titlesec}  % needed for colored section headings
%\usepackage[compact]{titlesec}  % reduce the spacing around section headings
"""
    if section_headings == 'blue':
        INTRO['latex'] += r"""
% --- section/subsection headings with blue color ---
\definecolor{seccolor}{cmyk}{.9,.5,0,.35}  % siamltexmm.sty section color
\titleformat{name=\section}
{\color{seccolor}\normalfont\Large\bfseries}
{\color{seccolor}\thesection}{1em}{}
\titleformat{name=\subsection}
{\color{seccolor}\normalfont\large\bfseries}
{\color{seccolor}\thesubsection}{1em}{}
\titleformat{name=\paragraph}[runin]
{\color{seccolor}\normalfont\normalsize\bfseries}
{}{}{\indent}
"""
        if option('latex_fancy_header'):
            INTRO['latex'] += r"""
% let the header have a thick gray hrule with section and page in blue above
\renewcommand{\headrulewidth}{0.4pt}
\renewcommand{\headrule}{{\color{gray!50}%
\hrule width\headwidth height\headrulewidth \vskip-\headrulewidth}}
\fancyhead[LE,RO]{{\color{seccolor}\rightmark}} %section
\fancyhead[RE,LO]{{\color{seccolor}\thepage}}
"""
    elif section_headings == 'strongblue':
        INTRO['latex'] += r"""
% --- section/subsection headings with a strong blue color ---
\definecolor{seccolor}{rgb}{0.2,0.2,0.8}
\titleformat{name=\section}
{\color{seccolor}\normalfont\Large\bfseries}
{\color{seccolor}\thesection}{1em}{}
\titleformat{name=\subsection}
{\color{seccolor}\normalfont\large\bfseries}
{\color{seccolor}\thesubsection}{1em}{}
\titleformat{name=\paragraph}[runin]
{\color{seccolor}\normalfont\normalsize\bfseries}
{}{}{\indent}
"""
    elif section_headings == 'gray':
        INTRO['latex'] += r"""
% --- section headings with white text on gray background, wide as heading ---
\titleformat{name=\section}[block]
  {\sffamily\Large}{}{0pt}{\colorsection}
\titlespacing*{\section}{0pt}{\baselineskip}{\baselineskip}

\newcommand{\colorsection}[1]{%
  \colorbox{gray!50}{{\color{white}\thesection\ #1}}}

\titleformat{name=\subsection}[block]
  {\sffamily\large}{}{0pt}{\colorsubsection}
\titlespacing*{\subsection}{0pt}{\baselineskip}{\baselineskip}

\newcommand{\colorsubsection}[1]{%
  \colorbox{gray!50}{{\color{white}\thesubsection\ #1}}}
"""
    elif section_headings == 'gray-wide':
        INTRO['latex'] += r"""
% --- section headings with white text on gray background, wide as textwidth ---
\titleformat{name=\section}[block]
  {\sffamily\Large}{}{0pt}{\colorsection}
\titlespacing*{\section}{0pt}{\baselineskip}{\baselineskip}

\newcommand{\colorsection}[1]{%
  \colorbox{gray!50}{\parbox{\dimexpr\textwidth-2\fboxsep}%
           {\color{white}\thesection\ #1}}}

\titleformat{name=\subsection}[block]
  {\sffamily\large}{}{0pt}{\colorsubsection}
\titlespacing*{\subsection}{0pt}{\baselineskip}{\baselineskip}

\newcommand{\colorsubsection}[1]{%
  \colorbox{gray!50}{\parbox{\dimexpr\textwidth-2\fboxsep}%
           {\color{white}\thesubsection\ #1}}}
""" % vars()

    if colored_table_rows not in ('gray', 'blue', 'no'):
        colored_table_rows = 'gray'
    if colored_table_rows != 'no':
        INTRO['latex'] += r"""

% --- color every two table rows ---
\let\oldtabular\tabular
\let\endoldtabular\endtabular"""
    if colored_table_rows == 'gray':
        INTRO['latex'] += r"""
\definecolor{rowgray}{gray}{0.9}
\renewenvironment{tabular}{\rowcolors{2}{white}{rowgray}%
\oldtabular}{\endoldtabular}

"""
    elif colored_table_rows == 'blue':
        INTRO['latex'] += r"""
\definecolor{appleblue}{rgb}{0.93,0.95,1.0}  % Apple blue
\renewenvironment{tabular}{\rowcolors{2}{white}{appleblue}%
\oldtabular}{\endoldtabular}

"""
    # Note: the line above is key for extracting the correct part
    # of the preamble for beamer slides in misc.slides_beamer

    # pdflatex needs calc package for emojis
    if re.search(INLINE_TAGS['emoji'], filestr):
        if not ',calc' in INTRO['latex']:
            INTRO['latex'] += '\n\\usepackage{calc}\n'

    # Make exercise, problem and project counters
    exer_envirs = ['Exercise', 'Problem', 'Project']
    exer_envirs = exer_envirs + ['{%s}' % e for e in exer_envirs]
    for exer_envir in exer_envirs:
        if exer_envir + ':' in filestr:
            INTRO['latex'] += r"""
\newenvironment{doconceexercise}{}{}
\newcounter{doconceexercisecounter}
"""
            exercise_numbering = option('latex_exercise_numbering=', 'absolute')
            if chapters and exercise_numbering == 'chapter':
                INTRO['latex'] += r"""
% Let exercises, problems, and projects be numbered per chapter:
\usepackage{chngcntr}
\counterwithin{doconceexercisecounter}{chapter}
"""
            if latex_style != 'Springer_T2':
                INTRO['latex'] += r"""

% ------ header in subexercises ------
%\newcommand{\subex}[1]{\paragraph{#1}}
%\newcommand{\subex}[1]{\par\vspace{1.7mm}\noindent{\bf #1}\ \ }
\makeatletter
% 1.5ex is the spacing above the header, 0.5em the spacing after subex title
\newcommand\subex{\@startsection{paragraph}{4}{\z@}%
                  {1.5ex\@plus1ex \@minus.2ex}%
                  {-0.5em}%
                  {\normalfont\normalsize\bfseries}}
\makeatother

"""
            else:
                INTRO['latex'] += r"""
% \subex{} is defined in t2do.sty
"""

            break

    if chapters and latex_style not in ("Koma_Script", "Springer_T2", "Springer_lnup"):
        # Follow advice from fancyhdr: redefine \cleardoublepage
        # see http://www.tex.ac.uk/cgi-bin/texfaq2html?label=reallyblank
        # (Koma has its own solution to the problem, svmono.cls has the command)
        INTRO['latex'] += r"""
% Make sure blank even-numbered pages before new chapters are
% totally blank with no header
\newcommand{\clearemptydoublepage}{\clearpage{\pagestyle{empty}\cleardoublepage}}
%\let\cleardoublepage\clearemptydoublepage % caused error in the toc
"""

    INTRO['latex'] += r"""
% --- end of standard preamble for documents ---
"""

    if '!bu-' in filestr:
        INTRO['latex'] += r"""
%%% USER-DEFINED ENVIRONMENTS
"""
    INTRO['latex'] += r"""
% USER PREAMBLE
% insert custom LaTeX commands...

\raggedbottom
\makeindex

%-------------------- end preamble ----------------------

\begin{document}

% endif for #ifdef PREAMBLE
% #endif

"""
    if preamble_complete:
        INTRO['latex'] = preamble + r"""
\begin{document}

"""
    elif preamble:
        # Insert user-provided part of the preamble
        INTRO['latex'] = INTRO['latex'].replace('% USER PREAMBLE', preamble)
    else:
        INTRO['latex'] = INTRO['latex'].replace('% USER PREAMBLE', '')

    if option('device=', '') == 'paper':
        INTRO['latex'] = INTRO['latex'].replace('oneside,', 'twoside,')

    newcommands_files = list(sorted([name
                                     for name in glob.glob('newcommands*.tex')
                                     if not name.endswith('.p.tex')]))
    for filename in newcommands_files:
        if os.path.isfile(filename):
            INTRO['latex'] += r"""\input{%s}
""" % (filename[:-4])
            #print '... found', filename
        #elif os.path.isfile(pfilename):
        #    print '%s exists, but not %s - run ptex2tex first' % \
        #    (pfilename, filename)
        else:
            #print '... did not find', filename
            pass

    if chapters:
        # Let a document with chapters have Index on a new
        # page and in the toc
        OUTRO['latex'] = r"""

% #ifdef PREAMBLE
\clearemptydoublepage
\markboth{Index}{Index}
\thispagestyle{empty}
\printindex

\end{document}
% #endif
"""
    else:
        OUTRO['latex'] = r"""

% #ifdef PREAMBLE
\printindex

\end{document}
% #endif
"""


def fix_latex_command_regex(pattern, application='match'):
    """
    Given a pattern for a regular expression match or substitution,
    the function checks for problematic patterns commonly
    encountered when working with LaTeX texts, namely commands
    starting with a backslash.

    For a pattern to be matched or substituted, and extra backslash is
    always needed (either a special regex construction like ``\w`` leads
    to wrong match, or ``\c`` leads to wrong substitution since ``\`` just
    escapes ``c`` so only the ``c`` is replaced, leaving an undesired
    backslash). For the replacement pattern in a substitutions, specified
    by the ``application='replacement'`` argument, a backslash
    before any of the characters ``abfgnrtv`` must be preceeded by an
    additional backslash.

    The application variable equals 'match' if `pattern` is used for
    a match and 'replacement' if `pattern` defines a replacement
    regex in a ``re.sub`` command.

    Caveats: let `pattern` just contain LaTeX commands, not combination
    of commands and other regular expressions (``\s``, ``\d``, etc.) as the
    latter will end up with an extra undesired backslash.

    Here are examples on failures.

    >>> re.sub(r'\begin\{equation\}', r'\[', r'\begin{equation}')
    '\\begin{equation}'
    >>> # match of mbox, not \mbox, and wrong output
    >>> re.sub(r'\mbox\{(.+?)\}', r'\fbox{\g<1>}', r'\mbox{not}')
    '\\\x0cbox{not}'

    Here are examples on using this function.

    >>> from doconce.latex import fix_latex_command_regex as fix
    >>> pattern = fix(r'\begin\{equation\}', application='match')
    >>> re.sub(pattern, r'\[', r'\begin{equation}')
    '\\['
    >>> pattern = fix(r'\mbox\{(.+?)\}', application='match')
    >>> replacement = fix(r'\fbox{\g<1>}', application='replacement')
    >>> re.sub(pattern, replacement, r'\mbox{not}')
    '\\fbox{not}'

    Avoid mixing LaTeX commands and ordinary regular expression
    commands, e.g.,

    >>> pattern = fix(r'\mbox\{(\d+)\}', application='match')
    >>> pattern
    '\\\\mbox\\{(\\\\d+)\\}'
    >>> re.sub(pattern, replacement, r'\mbox{987}')
    '\\mbox{987}'  # no substitution, no match
    >>> # \g<1> and similar works fine

    """
    import string
    problematic_letters = string.ascii_letters if application == 'match' \
                          else 'abfgnrtv'

    for letter in problematic_letters:
        problematic_pattern = '\\' + letter

        if letter == 'g' and application == 'replacement':
            # no extra \ for \g<...> in pattern
            if r'\g<' in pattern:
                continue

        ok_pattern = '\\\\' + letter
        if problematic_pattern in pattern and not ok_pattern in pattern:
            pattern = pattern.replace(problematic_pattern, ok_pattern)
    return pattern
