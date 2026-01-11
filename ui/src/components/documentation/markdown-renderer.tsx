import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeSlug from 'rehype-slug'
import { cn } from '@/lib/utils'

interface MarkdownRendererProps {
  content: string
  className?: string
}

export function MarkdownRenderer({ content, className }: MarkdownRendererProps) {
  return (
    <div className={cn("prose dark:prose-invert max-w-none", className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeSlug]}
        components={{
           img: ({node, ...props}) => (
               <span className="block my-6">
                 <img {...props} className="rounded-lg border shadow-sm max-w-full h-auto mx-auto" style={{ maxHeight: '500px' }} />
                 {props.alt && (
                     <span className="block text-center text-sm text-muted-foreground mt-2">
                         {props.alt}
                     </span>
                 )}
               </span>
           ),
           h1: ({node, ...props}) => <h1 className="scroll-m-20 text-4xl font-extrabold tracking-tight lg:text-5xl mb-8" {...props} />,
           h2: ({node, ...props}) => <h2 className="scroll-m-20 border-b pb-2 text-3xl font-semibold tracking-tight first:mt-0 mt-10 mb-4" {...props} />,
           h3: ({node, ...props}) => <h3 className="scroll-m-20 text-2xl font-semibold tracking-tight mt-8 mb-4" {...props} />,
           h4: ({node, ...props}) => <h4 className="scroll-m-20 text-xl font-semibold tracking-tight mt-6 mb-3" {...props} />,
           p: ({node, ...props}) => <p className="leading-7 [&:not(:first-child)]:mt-6" {...props} />,
           ul: ({node, ...props}) => <ul className="my-6 ml-6 list-disc [&>li]:mt-2" {...props} />,
           li: ({node, ...props}) => <li className="" {...props} />,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}
